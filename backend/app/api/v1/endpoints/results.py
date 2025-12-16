from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.result import Result
from app.models.task import Task
from app.models.upload import Upload
from app.services.storage import storage_service
from app.schemas.result import ResultResponse, ResultsListResponse
from datetime import datetime

router = APIRouter()
@router.get("/results", response_model=ResultsListResponse)
async def list_results(
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    algorithm: str | None = None,
    upload_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
):
    """List results with optional filtering and pagination."""
    base = db.query(Result, Task, Upload).join(Task, Result.task_id == Task.id).join(Upload, Task.upload_id == Upload.id)

    if algorithm:
        base = base.filter(Result.algorithm == algorithm)
    if upload_id:
        base = base.filter(Task.upload_id == upload_id)
    if date_from:
        base = base.filter(Result.created_at >= date_from)
    if date_to:
        base = base.filter(Result.created_at <= date_to)

    total = base.count()
    rows = (
        base.order_by(Result.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for r, t, u in rows:
        has_png = bool((r.result_metadata or {}).get("png_key"))
        items.append({
            "result_id": r.id,
            "task_id": r.task_id,
            "status": t.status,
            "algorithm": r.algorithm,
            "created_at": r.created_at,
            "completed_at": t.completed_at,
            "upload_id": u.id,
            "upload_filename": u.filename,
            "num_states": r.num_states,
            "num_edges": r.num_edges,
            "has_png": has_png,
        })

    return {"total": total, "items": items}



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


@router.delete("/results/{task_id}")
async def delete_result(
    task_id: int,
    db: Session = Depends(get_db)
):
    """Delete a result and its associated files."""
    result = db.query(Result).filter(Result.task_id == task_id).first()
    if not result:
        raise HTTPException(404, "Result not found")
    
    # Delete associated files from storage
    try:
        storage_service.delete_file(result.graph_storage_key)
    except Exception:
        pass  # Continue even if file deletion fails
    
    # Delete PNG if it exists
    png_key = (result.result_metadata or {}).get('png_key')
    if png_key:
        try:
            storage_service.delete_file(png_key)
        except Exception:
            pass
    
    # Delete result record from database
    db.delete(result)
    db.commit()
    
    return {"message": "Result deleted successfully"}
