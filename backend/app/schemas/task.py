from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any


class TaskParameters(BaseModel):
    use_iita: bool = False
    iita_max_diff: float = 0.08
    generations: int = 50
    patience: int = 20
    parallel: bool = True
    use_matrix_completion: bool = True


class TaskCreate(BaseModel):
    upload_id: int
    parameters: TaskParameters


class TaskResponse(BaseModel):
    id: int
    upload_id: int
    status: str
    celery_task_id: str | None
    parameters: Dict[str, Any]
    progress_percent: int
    current_generation: int | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    
    class Config:
        from_attributes = True
