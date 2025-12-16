from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.storage import storage_service
from app.models.upload import Upload
from app.schemas.upload import UploadResponse
import pandas as pd
import io
from typing import List

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload CSV file"""
    # Validate CSV
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "Only CSV files allowed")
    
    # Read CSV content
    content = await file.read()
    # Enforce max upload size (100MB)
    max_size_bytes = 100 * 1024 * 1024
    if len(content) > max_size_bytes:
        raise HTTPException(413, "File too large. Maximum allowed size is 100MB.")
    
    # Parse CSV to get metadata (auto-detect delimiter)
    try:
        # Use Python engine with sep=None to infer delimiter (comma, semicolon, tabs, etc.)
        df = pd.read_csv(io.BytesIO(content), sep=None, engine='python')
        num_rows = len(df)
        num_columns = len(df.columns)
    except Exception:
        # Fallback attempts with common delimiters for robustness
        for delim in [',', ';', '\t', '|']:
            try:
                df = pd.read_csv(io.BytesIO(content), sep=delim)
                num_rows = len(df)
                num_columns = len(df.columns)
                break
            except Exception:
                df = None
        if df is None:
            raise HTTPException(400, "Invalid CSV file: unable to parse with common delimiters")
    
    # Save to storage
    storage_key = storage_service.save_upload(content, file.filename)
    
    # Save to DB
    upload = Upload(
        filename=file.filename,
        original_filename=file.filename,
        storage_key=storage_key,
        file_size_bytes=len(content),
        num_rows=num_rows,
        num_columns=num_columns
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    
    return upload


@router.get("/uploads", response_model=List[UploadResponse])
async def list_uploads(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List recent uploads"""
    uploads = db.query(Upload).order_by(Upload.uploaded_at.desc()).limit(limit).all()
    return uploads


@router.get("/uploads/{upload_id}", response_model=UploadResponse)
async def get_upload(
    upload_id: int,
    db: Session = Depends(get_db)
):
    """Get upload by ID"""
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(404, "Upload not found")
    return upload
