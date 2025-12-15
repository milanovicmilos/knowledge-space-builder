from pydantic import BaseModel
from datetime import datetime


class UploadBase(BaseModel):
    filename: str
    original_filename: str


class UploadCreate(UploadBase):
    storage_key: str
    file_size_bytes: int
    num_rows: int | None = None
    num_columns: int | None = None


class UploadResponse(UploadBase):
    id: int
    storage_key: str
    file_size_bytes: int
    num_rows: int | None
    num_columns: int | None
    uploaded_at: datetime
    
    class Config:
        from_attributes = True
