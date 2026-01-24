"""
Analysis Endpoints - Most između Frontend-a i Learning Space Generator-a

Backend čuva sve u PostgreSQL i komunicira sa LSG preko Celery tasks-a.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config import settings
from app.database import get_db
from app.models.upload import Upload
from app.models.task import Task
from app.models.result import Result
from app.celery_app.tasks import run_learning_space_generator

router = APIRouter()


@router.post("/run")
async def run_analysis(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Pokreni novu analizu
    
    Workflow:
    1. Sačuvaj CSV u storage/uploads/
    2. Kreiraj Upload zapis u bazi
    3. Kreiraj Task zapis u bazi
    4. Pokreni Celery task (asinhrono)
    5. Vrati task_id klijentu
    """
    
    # Validacija
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are allowed"
        )
    
    # Sačuvaj datoteku
    upload_dir = Path(settings.UPLOAD_PATH)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"{timestamp}_{file.filename}"
    csv_path = upload_dir / csv_filename
    
    try:
        content = await file.read()
        with open(csv_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )
    
    try:
        # Kreiraj Upload zapis u bazi
        upload = Upload(
            filename=csv_filename,
            original_filename=file.filename,
            storage_key=csv_filename,
            file_size_bytes=len(content),
            num_rows=0,  # TODO: parse CSV
            num_columns=0,
        )
        db.add(upload)
        db.commit()
        db.refresh(upload)
        
        # Kreiraj Task zapis u bazi
        task = Task(
            upload_id=upload.id,
            status="pending",
            progress=0,
            message="Initializing analysis...",
            parameters={}
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # Pokreni Celery task (asinhrono)
        celery_task = run_learning_space_generator.delay(
            task_id=task.id,
            upload_id=upload.id,
            csv_path=str(csv_path)
        )
        
        # Sačuvaj Celery task ID
        task.celery_task_id = celery_task.id
        db.commit()
        
        return {
            "task_id": task.id,
            "status": task.status,
            "progress": task.progress,
            "message": task.message
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create task: {str(e)}"
        )


@router.get("/{task_id}/status")
async def get_task_status(task_id: int, db: Session = Depends(get_db)):
    """
    Prati status zadatka
    """
    
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    return {
        "task_id": task.id,
        "status": task.status,
        "progress": task.progress,
        "message": task.message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "error_message": task.error_message
    }


@router.get("/{task_id}/statistics")
async def get_analysis_statistics(task_id: int, db: Session = Depends(get_db)):
    """
    Preuzmi statističke brojeve iz baze
    """
    
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    if task.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Task not completed yet"
        )
    
    # Pronađi rezultate
    result = db.query(Result).filter(Result.task_id == task_id).first()
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Results not found"
        )
    
    return {
        "task_id": task_id,
        "status": task.status,
        "total_items": result.total_items,
        "total_concepts": result.total_concepts,
        "total_students": result.total_students,
        "knowledge_space_states": result.knowledge_space_states,
        "prerequisites_found": result.prerequisites_found,
        "semantic_clusters": result.semantic_clusters,
        "root_concepts": result.root_concepts
    }


@router.get("/{task_id}/visualization")
async def get_analysis_visualization(task_id: int, db: Session = Depends(get_db)):
    """
    Preuzmi putanju do PNG vizuelizacije
    """
    
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    if task.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Task not completed yet"
        )
    
    result = db.query(Result).filter(Result.task_id == task_id).first()
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Results not found"
        )
    
    # Pronađi PNG fajl
    if not result.result_files or "knowledge_structure_graph.png" not in result.result_files:
        raise HTTPException(
            status_code=404,
            detail="Visualization not found"
        )
    
    png_path = result.result_files["knowledge_structure_graph.png"]
    
    return {
        "task_id": task_id,
        "graph_file": png_path,
        "graph_exists": True
    }


@router.get("/{task_id}/files")
async def list_result_files(task_id: int, db: Session = Depends(get_db)):
    """
    Lista svi dostupni fajlovi
    """
    
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    if task.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Task not completed yet"
        )
    
    result = db.query(Result).filter(Result.task_id == task_id).first()
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Results not found"
        )
    
    if not result.result_files:
        return {
            "task_id": task_id,
            "files": []
        }
    
    # Konvertuj file dictionary u list
    files = []
    for filename, filepath in result.result_files.items():
        file_path = Path(filepath)
        if file_path.exists():
            files.append({
                "name": filename,
                "path": str(filepath),
                "size": file_path.stat().st_size
            })
        else:
            files.append({
                "name": filename,
                "path": str(filepath),
                "size": 0,
                "error": "File not found on disk"
            })
    
    return {
        "task_id": task_id,
        "files": files
    }


@router.get("/{task_id}/download/{filename}")
async def download_result_file(task_id: int, filename: str, db: Session = Depends(get_db)):
    """
    Preuzmi specifičan fajl iz rezultata
    """
    
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    if task.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Task not completed yet"
        )
    
    result = db.query(Result).filter(Result.task_id == task_id).first()
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Results not found"
        )
    
    # Pronađi fajl
    if not result.result_files or filename not in result.result_files:
        raise HTTPException(
            status_code=404,
            detail=f"File '{filename}' not found"
        )
    
    filepath = Path(result.result_files[filename])
    
    if not filepath.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found on disk: {filepath}"
        )
    
    # Odredi media type
    if filename.endswith('.json'):
        media_type = "application/json"
    elif filename.endswith('.csv'):
        media_type = "text/csv"
    elif filename.endswith('.png'):
        media_type = "image/png"
    elif filename.endswith('.ttl'):
        media_type = "text/turtle"
    else:
        media_type = "application/octet-stream"
    
    # Vrati fajl
    return FileResponse(
        path=str(filepath),
        media_type=media_type,
        filename=filename
    )


@router.get("/{task_id}/knowledge-space", response_model=dict)
async def get_knowledge_space(task_id: int, db: Session = Depends(get_db)):
    """
    Učitaj knowledge_space.json iz baze ili fajla
    Za frontend GraphModal
    """
    
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    if task.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Analysis not completed yet"
        )
    
    # Pronađi rezultate
    result = db.query(Result).filter(Result.task_id == task_id).first()
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Results not found"
        )
    
    # Prvo pokušaj iz baze
    if result.knowledge_space:
        return {"knowledge_space": result.knowledge_space}
    
    # Ako nije u bazi, pokušaj iz fajla (backward compatibility)
    if result.result_files and "knowledge_space.json" in result.result_files:
        try:
            filepath = Path(result.result_files["knowledge_space.json"])
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    knowledge_space = json.load(f)
                    # Sačuvaj u bazu za budućnost
                    result.knowledge_space = knowledge_space
                    db.commit()
                    return {"knowledge_space": knowledge_space}
        except Exception as e:
            print(f"Error reading knowledge_space.json from file: {e}")
    
    raise HTTPException(
        status_code=404,
        detail="Knowledge space data not found"
    )


@router.get("/tasks")
async def get_all_tasks(db: Session = Depends(get_db)):
    """
    Get list of all tasks with their statistics
    """
    
    tasks = db.query(Task).order_by(desc(Task.created_at)).all()
    
    result_list = []
    for task in tasks:
        # Get result statistics if available
        result = db.query(Result).filter(Result.task_id == task.id).first()
        
        # Get upload info
        upload = db.query(Upload).filter(Upload.id == task.upload_id).first()
        
        task_data = {
            "task_id": task.id,
            "status": task.status,
            "progress": task.progress,
            "message": task.message,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message,
            "upload_filename": upload.original_filename if upload else None,
        }
        
        # Add result statistics if completed
        if result:
            task_data.update({
                "total_items": result.total_items,
                "total_concepts": result.total_concepts,
                "total_students": result.total_students,
                "knowledge_space_states": result.knowledge_space_states,
                "prerequisites_found": result.prerequisites_found,
                "semantic_clusters": result.semantic_clusters,
                "root_concepts": result.root_concepts,
            })
        
        result_list.append(task_data)
    
    return {
        "tasks": result_list,
        "total_count": len(result_list)
    }


@router.delete("/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    """
    Delete a task and all associated data (results, uploads, files)
    """
    
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    try:
        # Delete associated files from disk
        result = db.query(Result).filter(Result.task_id == task_id).first()
        if result and result.result_files:
            for filepath in result.result_files.values():
                try:
                    file_path = Path(filepath)
                    if file_path.exists():
                        file_path.unlink()
                except Exception as e:
                    print(f"Warning: Could not delete file {filepath}: {e}")
        
        # Delete result from database
        if result:
            db.delete(result)
        
        # Delete uploaded CSV file
        upload = db.query(Upload).filter(Upload.id == task.upload_id).first()
        if upload:
            try:
                upload_path = Path(settings.UPLOAD_PATH) / upload.storage_key
                if upload_path.exists():
                    upload_path.unlink()
            except Exception as e:
                print(f"Warning: Could not delete upload file: {e}")
            
            db.delete(upload)
        
        # Delete task
        db.delete(task)
        db.commit()
        
        return {
            "success": True,
            "message": f"Task {task_id} and all associated data deleted successfully"
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete task: {str(e)}"
        )
