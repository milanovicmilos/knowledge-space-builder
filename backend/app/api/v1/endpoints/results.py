from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.result import Result
from app.services.storage import storage_service
from app.schemas.result import ResultResponse

router = APIRouter()


@router.get("/results/{task_id}", response_model=ResultResponse)
async def get_result(
    task_id: int,
    db: Session = Depends(get_db)
):
    """Get result by task ID"""
    result = db.query(Result).filter(Result.task_id == task_id).first()
    if not result:
        raise HTTPException(404, "Result not found")
    return result


@router.get("/results/{task_id}/download")
async def download_result(
    task_id: int,
    db: Session = Depends(get_db)
):
    """Download result JSON file"""
    result = db.query(Result).filter(Result.task_id == task_id).first()
    if not result:
        raise HTTPException(404, "Result not found")
    
    file_path = storage_service.get_file_path(result.graph_storage_key)
    return FileResponse(
        path=file_path,
        media_type='application/json',
        filename=f'result_{task_id}.json'
    )
