from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any


class TaskParameters(BaseModel):
    # Algorithm selection
    use_iita: bool = False
    
    # IITA options
    iita_max_diff: float = 0.08
    
    # NEAT options
    generations: int = 50
    patience: int = 20
    parallel: bool = True
    greedy: bool = False  # Run until first valid solution
    plot: bool = False  # Show graph during evolution
    
    # Data options
    randomize_items: bool = False
    use_matrix_completion: bool = True
    clear_cache: bool = False
    
    # Output options
    generate_png: bool = True  # Generate PNG visualization
    png_filename: str | None = None


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
    progress_details: Dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    
    class Config:
        from_attributes = True
