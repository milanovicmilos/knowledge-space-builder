from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.task import Task
from app.models.upload import Upload
from app.schemas.task import TaskCreate, TaskResponse
from app.celery_app.tasks import run_algorithm_task
from typing import List

router = APIRouter()


@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db)
):
    """Create and start a new task"""
    # Verify upload exists
    upload = db.query(Upload).filter(Upload.id == task_data.upload_id).first()
    if not upload:
        raise HTTPException(404, "Upload not found")
    
    # Create task record
    task = Task(
        upload_id=task_data.upload_id,
        parameters=task_data.parameters.model_dump(),
        status="pending"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Start Celery task
    celery_task = run_algorithm_task.delay(
        task_id=task.id,
        upload_id=task_data.upload_id,
        parameters=task_data.parameters.model_dump()
    )
    
    # Update with Celery task ID
    task.celery_task_id = celery_task.id
    db.commit()
    db.refresh(task)
    
    return task


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """Get task status by ID"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List recent tasks"""
    tasks = db.query(Task).order_by(Task.created_at.desc()).limit(limit).all()
    return tasks
