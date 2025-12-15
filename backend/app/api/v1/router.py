from fastapi import APIRouter
from app.api.v1.endpoints import uploads, tasks, results

api_router = APIRouter()

api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(results.router, prefix="/results", tags=["results"])
