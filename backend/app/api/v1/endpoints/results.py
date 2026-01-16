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
@router.get("", response_model=ResultsListResponse)
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

    # Note: algorithm filter removed as Result model doesn't have algorithm column
    # Algorithm info is in Task.parameters['mode']
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
        # Extract algorithm from task parameters if available
        algorithm = (t.parameters or {}).get('mode', 'unknown')
        items.append({
            "result_id": r.id,
            "task_id": r.task_id,
            "status": t.status,
            "algorithm": algorithm,
            "created_at": r.created_at,
            "completed_at": t.completed_at,
            "upload_id": u.id,
            "upload_filename": u.filename,
            "num_states": r.num_states,
            "num_edges": r.num_edges,
            "has_png": has_png,
        })

    return {"total": total, "items": items}



@router.get("/{task_id}", response_model=ResultResponse)
async def get_result(
    task_id: int,
    db: Session = Depends(get_db)
):
    """Get result by task ID with learning space data"""
    result = db.query(Result).filter(Result.task_id == task_id).first()
    if not result:
        raise HTTPException(404, "Result not found")
    
    # Load learning space from storage
    try:
        import json
        file_path = storage_service.get_file_path(result.graph_storage_key)
        with open(file_path, 'r') as f:
            learning_space_data = json.load(f)
    except Exception:
        learning_space_data = None
    
    # Add learning space to result (not in DB model, but in API response)
    meta = result.result_metadata or {}
    
    result_dict = {
        "id": result.id,
        "task_id": result.task_id,
        "graph_storage_key": result.graph_storage_key,
        "num_states": result.num_states,
        "num_edges": result.num_edges,
        "num_relations": meta.get("num_relations"),
        "discrepancy": meta.get("discrepancy"),
        "is_valid": meta.get("is_valid"),
        "algorithm": meta.get("algorithm"),
        "final_generation": meta.get("final_generation"),
        "execution_time_seconds": result.execution_time_seconds,
        "result_metadata": meta,
        "created_at": result.created_at,
        "learning_space": learning_space_data
    }
    return result_dict


@router.get("/{task_id}/download")
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


@router.delete("/{task_id}")
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
