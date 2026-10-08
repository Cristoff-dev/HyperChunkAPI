# HyperChunkAPI: Enterprise Async Data Ingestion Pipeline

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Celery](https://img.shields.io/badge/celery-%2337814A.svg?&style=for-the-badge&logo=celery&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/postgresql-4169e1?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?style=for-the-badge&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)

## 📌 Context & Business Value
In fast-paced e-commerce and logistics sectors, processing massive supplier inventories and billing reports via CSV/Excel is a daily requirement. Standard parsing scripts often suffer from Out-Of-Memory (OOM) crashes on large payloads or leave databases in corrupted partial states when validation fails halfway through.

**HyperChunkAPI** is a containerized, asynchronous ETL microservice built to solve this. It guarantees **O(1) memory consumption**, strictly enforces **data integrity (ACID)**, and provides instant HTTP responses by delegating heavy processing to background workers.

## 🏗️ Architectural Highlights
- **Stream-Driven Processing:** Uses Python generators to read massive files line-by-line. The memory footprint remains stable at ~45MB whether processing 10,000 or 1,000,000 rows.
- **ACID "All-or-Nothing" Transactions:** Implements strict SQLAlchemy transactional context blocks (`db.begin()`). If a single row fails Pydantic validation (e.g., malformed email), the entire batch is rolled back (`db.rollback()`), guaranteeing a clean database state.
- **Event-Driven Background Workers:** File uploads are instantly buffered to temporary blob storage. The API returns a `202 Accepted` instantly, offloading the ETL process to **Celery** workers via a **Redis** message broker.
- **Bulk Insert Optimization:** Validated records are batched and committed via `bulk_save_objects()` to drastically reduce database I/O latency.

## 📂 Project Structure
```text
app/
├── api/          # FastAPI routing (Upload handlers)
├── core/         # Environment config & SQLAlchemy engine setup
├── models/       # SQLAlchemy declarative base (Database layer)
├── schemas/      # Pydantic models (Strict payload validation layer)
├── services/     # Core ETL logic (Stream processing, chunking, ACID control)
└── worker/       # Celery application & asynchronous task definitions
```

## 🚀 Quick Start (Dockerized)
The entire infrastructure is orchestrated via Docker Compose for zero-configuration, reproducible deployments.

### 1. Spin up the cluster
```bash
docker-compose up --build
```
*(This initializes FastAPI, PostgreSQL, Redis, and the Celery Worker).*

### 2. Trigger an Ingestion Task
Submit a large CSV payload. The endpoint will instantly return a tracking ID.
```bash
curl -X POST "http://localhost:8000/api/v1/ingest/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@test_payload.csv"
```

**Immediate 202 Response:**
```json
{
  "status": "processing",
  "message": "Payload accepted for asynchronous ingestion.",
  "task_id": "284dc5f7-de0c-41a7-b761-8bbdc9c28e8f",
  "file_reference": "uuid_test_payload.csv"
}
```

## 🛡️ Error Handling & Auditing
If validation fails during the background process, the database state remains untouched, and the worker outputs a structured JSON detailing the exact coordinates of the anomalies, ready for client review:

```json
{
  "status": "failed",
  "message": "Payload rejected due to validation constraints. Database state preserved.",
  "error_count": 1,
  "details": [
    {
      "row": 3,
      "errors": [
        {"column": "supplier_email", "reason": "value is not a valid email address"}
      ]
    }
  ]
}
```