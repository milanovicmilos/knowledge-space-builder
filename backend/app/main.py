from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.config import settings
from app.api.v1.router import api_router
from app.database import engine, Base
from app import models  # Ensure models are imported before create_all

# Create database tables (requires models imported)
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Web interface for Knowledge Space Generator - Bridge between frontend and LSG algorithm",
    version=settings.PROJECT_VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "message": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "status": "ready",
        "role": "Bridge between frontend and Learning Space Generator"
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "learning-space-generator-api"}


@app.get("/api/health")
async def api_health():
    return {"status": "ok", "service": "learning-space-generator-api"}

