from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any


class TaskParameters(BaseModel):
    # Item clustering options (NEW)
    cluster: bool = True  # Enable item clustering (always recommended)
    row_coverage_thresh: float = 0.8  # Minimum row coverage per cluster
    min_pairs: int = 500  # Minimum item pairs per cluster
    max_item_clusters: int | None = None  # Max clusters (auto if None)
    
    # NEAT options
    generations: int = 50
    patience: int = 20
    parallel: bool = True
    greedy: bool = False  # Run until first valid solution
    plot: bool = False  # Show graph during evolution
    
    # Missing value handling
    missing_match_reward: float = 0.5  # Reward for matching missing values
    missing_mismatch_penalty: float = 1.0  # Penalty for mismatched missing
    
    # Data options
    randomize_items: bool = False
    
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
