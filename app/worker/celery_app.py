import os
from celery import Celery
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.etl_processor import process_inventory_csv

# Initialize Celery instance binding to Redis broker
celery_worker = Celery(
    "hyperchunk_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configure serialization strictly to JSON to prevent pickle vulnerabilities
celery_worker.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_worker.task(bind=True, name="process_csv_task")
def process_csv_task(self, file_path: str, chunk_size: int = 1000):
    # Instantiate isolated database session per worker execution
    db = SessionLocal()
    try:
        # Delegate execution to the ETL service layer
        result = process_inventory_csv(file_path=file_path, db=db, chunk_size=chunk_size)
        return result
    except Exception as e:
        # Log critical worker failures
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()
        # Storage cleanup: purge temporary Blob Storage file post-processing
        if os.path.exists(file_path):
            os.remove(file_path)