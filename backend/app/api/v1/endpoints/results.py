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
    format: str = 'json',
    db: Session = Depends(get_db)
):
    """Download result file (JSON or PNG)"""
    result = db.query(Result).filter(Result.task_id == task_id).first()
    if not result:
        raise HTTPException(404, "Result not found")
    
    if format == 'png':
        # Get PNG from metadata
        png_key = result.result_metadata.get('png_key') if result.result_metadata else None
        if not png_key:
            raise HTTPException(404, "PNG visualization not available for this result")
        
        file_path = storage_service.get_file_path(png_key)
        return FileResponse(
            path=file_path,
            media_type='image/png',
            filename=f'learning_space_{task_id}.png'
        )
    else:
        # Default: JSON
        file_path = storage_service.get_file_path(result.graph_storage_key)
        return FileResponse(
            path=file_path,
            media_type='application/json',
            filename=f'learning_space_{task_id}.json'
        )
