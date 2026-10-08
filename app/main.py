from fastapi import FastAPI
from app.api.routes import router as ingest_router
from app.core.database import engine, Base

# Initialize database schema mapping mapping (Alembic recommended for production)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="HyperChunkAPI",
    description="High-performance, async ETL microservice for massive payload ingestion.",
    version="1.0.0"
)

# Register endpoint routers
app.include_router(ingest_router, prefix="/api/v1")

@app.get("/health", tags=["Monitoring"])
def health_check():
    # Liveness probe for Kubernetes / Docker Swarm health checks
    return {"status": "healthy", "service": "HyperChunkAPI"}