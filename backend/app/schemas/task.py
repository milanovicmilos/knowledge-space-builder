from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any


class TaskParameters(BaseModel):
    # Execution Mode
    mode: str = 'optimize'  # 'optimize' (recommended) or 'manual'
    n_trials: int = 3  # Number of optimization trials (only for optimize mode)

    # MIRT-VAE Training options (Manual mode or override)
    epochs: int = 8  # Number of training epochs
    latent_dim: int = 10  # Latent dimension size
    device: str = 'cpu'  # 'cpu' or 'cuda'
    
    # Prerequisite graph options
    pred_threshold: float = 0.6  # Prediction threshold for binarization
    implication_threshold: float = 0.85  # Threshold for prerequisite relations
    min_known: int = 5  # Minimum students who know item B
    
    # Lattice construction options
    select_k: int = 30  # Number of top items to select
    min_support: int = 7  # Minimum support for empirical states
    force_k: bool = False  # Force k without safety reduction
    
    # Output options
    generate_png: bool = True  # Generate PNG visualization


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
    current_epoch: int | None  # Changed from current_generation
    progress_details: Dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    
    class Config:
        from_attributes = True
