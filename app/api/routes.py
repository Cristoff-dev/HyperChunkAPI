import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.worker.celery_app import process_csv_task
from app.core.config import settings

router = APIRouter()

@router.post("/ingest/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_large_file(file: UploadFile = File(...)):
    # Validate MIME type to prevent malicious payload ingestion
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported media type. Strict .csv enforcement."
        )

    # Generate UUID for blob storage emulation to prevent filename collisions
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    # Stream file buffer directly to disk (I/O bound) to prevent RAM exhaustion
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Disk I/O failure during stream writing: {str(e)}"
        )

    # Dispatch asynchronous background task to Celery message broker
    task = process_csv_task.delay(file_path=file_path, chunk_size=1000)

    # Return 202 Accepted instantly with task tracking reference
    return {
        "status": "processing",
        "message": "Payload accepted for asynchronous ingestion.",
        "task_id": task.id,
        "file_reference": safe_filename
    }