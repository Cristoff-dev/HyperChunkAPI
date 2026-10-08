import csv
from typing import Dict, Any
from sqlalchemy.orm import Session
from pydantic import ValidationError
from app.schemas.validation import ProductRowSchema
from app.models.domain import Product

def process_inventory_csv(file_path: str, db: Session, chunk_size: int = 1000) -> Dict[str, Any]:
    errors = []
    valid_records = []
    total_processed = 0

    # Stream reading via generator to prevent memory overflow (OOM) on large payloads
    with open(file_path, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        
        try:
            # Initialize ACID transaction context block
            with db.begin(): 
                for row_number, row_data in enumerate(reader, start=2): # start=2 offsets header
                    total_processed += 1
                    
                    try:
                        # 1. Strict schema validation via Pydantic model
                        valid_data = ProductRowSchema(**row_data)
                        
                        # 2. Map validated schema to SQLAlchemy ORM instance
                        product_orm = Product(**valid_data.model_dump())
                        valid_records.append(product_orm)

                        # 3. Execute batch insert to optimize I/O and reduce network latency
                        if len(valid_records) >= chunk_size:
                            db.bulk_save_objects(valid_records)
                            valid_records.clear() # Free heap memory buffer
                            
                    except ValidationError as e:
                        # Parse Pydantic validation errors into structured dictionaries
                        error_details = [{"column": err["loc"][0], "reason": err["msg"]} for err in e.errors()]
                        errors.append({"row": row_number, "errors": error_details})

                # Flush remaining records buffer to database
                if valid_records:
                    db.bulk_save_objects(valid_records)

                # ALL-OR-NOTHING POLICY: Trigger explicit rollback if validation anomalies exist
                if errors:
                    db.rollback()
                    return {
                        "status": "failed",
                        "message": "Payload rejected due to validation constraints. Database state preserved.",
                        "total_scanned": total_processed,
                        "error_count": len(errors),
                        "details": errors
                    }

        except Exception as critical_error:
            # Catch unhandled exceptions (e.g., connection drops) and enforce rollback
            db.rollback()
            return {"status": "critical_error", "message": str(critical_error)}

    # Implicit commit executes successfully on context manager exit
    return {
        "status": "success",
        "message": "Payload processed and committed successfully.",
        "total_inserted": total_processed
    }