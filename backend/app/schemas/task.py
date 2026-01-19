from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any, Optional

class TaskParameters(BaseModel):
    # Execution Mode
    mode: str = 'lsg_pipeline' 
    n_trials: int = 3

    # LSG Options
    iita_threshold: float = 0.05
    semantic_weight: float = 0.3
    use_concept_level_iita: bool = True  # NEW: Run IITA on concepts (aggregated by LLM), not individual items

    # Legacy / Compatibility
    epochs: int = 8
    latent_dim: int = 10
    device: str = 'cpu'
    pred_threshold: float = 0.6
    implication_threshold: float = 0.85
    min_known: int = 5
    select_k: int = 30
    min_support: int = 7
    force_k: bool = False
    generate_png: bool = True


class TaskCreate(BaseModel):
    upload_id: int
    parameters: TaskParameters

class TaskResponse(BaseModel):
    id: int
    upload_id: int
    status: str
    progress_percent: int
    progress_details: Optional[Dict[str, Any]]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    parameters: Dict[str, Any]

    class Config:
        from_attributes = True

