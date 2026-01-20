"""
Analysis Endpoints - Most između Frontend-a i Learning Space Generator-a

Backend čuva sve u PostgreSQL i komunicira sa LSG preko Celery tasks-a.
"""

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

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
    1. Sačuvaj CSV fajl
    2. Kreiraj Upload zapis u bazi
    3. Kreiraj Task zapis u bazi
    4. Pokreni Celery task (asinhrono)
    5. Vrati task_id frontend-u
    """
    
    # Validacija
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are allowed"
        )
    
    # Kreiraj upload direktorijum (idempotentno)
    upload_dir = Path(settings.UPLOAD_PATH)
    upload_dir.parent.mkdir(parents=True, exist_ok=True)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Sačuvaj fajl
        content = await file.read()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"{timestamp}_{file.filename}"
        csv_path = upload_dir / csv_filename
        
        with open(csv_path, "wb") as f:
            f.write(content)
        
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
            message="Inicijalizujem analizu...",
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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start analysis: {str(e)}"
        )


@router.get("/{task_id}/status")
async def get_analysis_status(task_id: int, db: Session = Depends(get_db)):
    """
    Prati status analize iz baze
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


@router.get("/{task_id}/results")
async def get_analysis_results(task_id: int, db: Session = Depends(get_db)):
    """
    Preuzmi sve rezultate iz baze i fajlove
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
            detail=f"Task not completed yet. Current status: {task.status}"
        )
    
    # Pronađi rezultate
    result = db.query(Result).filter(Result.task_id == task_id).first()
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Results not found"
        )
    
    # Učitaj JSON fajlove
    files_data = {}
    if result.result_files:
        for filename, filepath in result.result_files.items():
            if filename.endswith('.json'):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        files_data[filename] = json.load(f)
                except:
                    files_data[filename] = {"_error": "Could not load file"}
    
    return {
        "task_id": task_id,
        "status": task.status,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "files": files_data
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
        "statistics": {
            "total_items": result.total_items,
            "total_concepts": result.total_concepts,
            "total_students": result.total_students,
            "knowledge_space_states": result.knowledge_space_states,
            "prerequisites_found": result.prerequisites_found,
            "semantic_clusters": result.semantic_clusters,
            "root_concepts": result.root_concepts
        }
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
    png_path = None
    if result.result_files:
        for filename, filepath in result.result_files.items():
            if filename.endswith('.png'):
                png_path = filepath
                break
    
    if not png_path:
        raise HTTPException(
            status_code=404,
            detail="Visualization not found"
        )
    
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
    
    files = []
    if result.result_files:
        for filename, filepath in result.result_files.items():
            try:
                size = Path(filepath).stat().st_size
            except:
                size = 0
            
            files.append({
                "name": filename,
                "size": size,
                "path": filepath
            })
    
    return {
        "task_id": task_id,
        "total_files": len(files),
        "files": files
    }


@router.get("/{task_id}/file/{filename}")
async def download_result_file(task_id: int, filename: str, db: Session = Depends(get_db)):
    """
    Preuzmi pojedinačni fajl iz rezultata analize
    
    Supports: JSON, CSV, PNG, TTL
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


class AnalysisManager:
    """Upravlja analizama - pokretanje, praćenje, rezultati"""

    @staticmethod
    def generate_task_id() -> str:
        """Generiši jedinstveni ID za analizu"""
        global _analysis_counter
        with _analysis_lock:
            _analysis_counter += 1
            return f"analysis_{_analysis_counter}"

    @staticmethod
    def create_analysis_record(task_id: str, filename: str) -> None:
        """Napravi zapis o novoj analizi"""
        _active_analyses[task_id] = {
            "task_id": task_id,
            "filename": filename,
            "status": "initializing",
            "progress": 0,
            "message": "Inicijalizujem analizu...",
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "result_files": {}
        }

    @staticmethod
    def update_analysis(task_id: str, status: str, progress: int, message: str) -> None:
        """Ažuriraj status analize"""
        if task_id in _active_analyses:
            analysis = _active_analyses[task_id]
            analysis["status"] = status
            analysis["progress"] = min(progress, 100)
            analysis["message"] = message
            if status == "running" and not analysis["started_at"]:
                analysis["started_at"] = datetime.now().isoformat()
            elif status == "completed":
                analysis["completed_at"] = datetime.now().isoformat()

    @staticmethod
    def run_learning_space_generator(task_id: str, csv_path: str) -> None:
        """Pokreni learning_space_generator kao subproces"""
        try:
            # Pripremi putanje
            lsg_path = Path(settings.LSG_PATH)
            venv_python = lsg_path / ".venv" / "Scripts" / "python.exe"
            script = lsg_path / settings.LSG_SCRIPT
            
            if not venv_python.exists():
                raise FileNotFoundError(f"Python executable not found: {venv_python}")
            
            if not script.exists():
                raise FileNotFoundError(f"Script not found: {script}")

            AnalysisManager.update_analysis(
                task_id, "running", 5, "Startanje Learning Space Generator-a..."
            )

            # Pokreni kao subproces
            # LSG će sam pisati u output/ folder
            process = subprocess.Popen(
                [str(venv_python), str(script), "full"],
                cwd=str(lsg_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            output_lines = []
            for line in process.stdout:
                output_lines.append(line.strip())
                
                # Parsiranje progresa iz output-a
                lower_line = line.lower()
                
                if "preprocessing" in lower_line:
                    AnalysisManager.update_analysis(
                        task_id, "running", 10, "Cleaning noisy data (DAE)..."
                    )
                elif "llm" in lower_line or "classification" in lower_line:
                    AnalysisManager.update_analysis(
                        task_id, "running", 20, "LLM item classification..."
                    )
                elif "semantic" in lower_line or "cluster" in lower_line:
                    AnalysisManager.update_analysis(
                        task_id, "running", 30, "Semantic clustering..."
                    )
                elif "aggregation" in lower_line:
                    AnalysisManager.update_analysis(
                        task_id, "running", 40, "Concept aggregation..."
                    )
                elif "difficulty" in lower_line:
                    AnalysisManager.update_analysis(
                        task_id, "running", 50, "Analyzing item difficulty..."
                    )
                elif "iita" in lower_line or "extraction" in lower_line:
                    AnalysisManager.update_analysis(
                        task_id, "running", 60, "IITA prerequisite extraction..."
                    )
                elif "knowledge" in lower_line or "space" in lower_line:
                    AnalysisManager.update_analysis(
                        task_id, "running", 75, "Generating knowledge space..."
                    )
                elif "visualization" in lower_line or "graph" in lower_line:
                    AnalysisManager.update_analysis(
                        task_id, "running", 85, "Creating visualization..."
                    )
                elif "ontology" in lower_line or "rdf" in lower_line:
                    AnalysisManager.update_analysis(
                        task_id, "running", 90, "Exporting RDF/TTL ontology..."
                    )

            # Sačekaj završetak procesa
            return_code = process.wait()
            
            if return_code != 0:
                stderr_output = process.stderr.read() if process.stderr else "Unknown error"
                raise RuntimeError(f"Learning Space Generator failed: {stderr_output}")

            # Pronađi i indeksuj rezultate
            output_dir = lsg_path / "output"
            if output_dir.exists():
                result_files = {}
                for file in output_dir.glob("*"):
                    if file.is_file():
                        result_files[file.name] = file.as_posix()
                
                _active_analyses[task_id]["result_files"] = result_files

            AnalysisManager.update_analysis(
                task_id, "completed", 100, "Analysis completed successfully!"
            )

        except Exception as e:
            AnalysisManager.update_analysis(
                task_id, "failed", 0, f"Error: {str(e)}"
            )
            print(f"[{task_id}] ERROR: {str(e)}")


@router.post("/run")
async def run_analysis(file: UploadFile = File(...)):
    """
    Pokreni novu analizu
    
    Primer:
    ```
    POST /api/v1/analysis/run
    Content-Type: multipart/form-data
    
    file: <CSV datoteka>
    ```
    
    Rezultat:
    ```json
    {
        "task_id": "analysis_1",
        "status": "initializing",
        "progress": 0,
        "message": "Inicijalizujem analizu..."
    }
    ```
    """
    
    # Validacija
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are allowed"
        )
    
    # Kreiraj upload direktorijum
    upload_dir = Path(settings.UPLOAD_PATH)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Sačuvaj datoteku
    task_id = AnalysisManager.generate_task_id()
    csv_filename = f"{task_id}_data.csv"
    csv_path = upload_dir / csv_filename
    
    try:
        content = await file.read()
        with open(csv_path, "wb") as f:
            f.write(content)
        
        # Napravi zapis o analizi
        AnalysisManager.create_analysis_record(task_id, file.filename)
        
        # Pokreni analizu u posebnoj niti (non-blocking)
        analysis_thread = threading.Thread(
            target=AnalysisManager.run_learning_space_generator,
            args=(task_id, str(csv_path))
        )
        analysis_thread.daemon = True
        analysis_thread.start()
        
        return {
            "task_id": task_id,
            "status": _active_analyses[task_id]["status"],
            "progress": _active_analyses[task_id]["progress"],
            "message": _active_analyses[task_id]["message"]
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start analysis: {str(e)}"
        )


@router.get("/{task_id}/status")
async def get_analysis_status(task_id: str):
    """
    Prati status analize
    
    Rezultat:
    ```json
    {
        "task_id": "analysis_1",
        "status": "running",
        "progress": 45,
        "message": "Concept aggregation...",
        "started_at": "2026-01-19T10:30:00",
        "completed_at": null
    }
    ```
    """
    
    if task_id not in _active_analyses:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found"
        )
    
    analysis = _active_analyses[task_id]
    return {
        "task_id": analysis["task_id"],
        "status": analysis["status"],
        "progress": analysis["progress"],
        "message": analysis["message"],
        "created_at": analysis["created_at"],
        "started_at": analysis["started_at"],
        "completed_at": analysis["completed_at"]
    }


@router.get("/{task_id}/results")
async def get_analysis_results(task_id: str):
    """
    Preuzmimo sve rezultate iz Learning Space Generator-a
    
    Rezultat:
    ```json
    {
        "task_id": "analysis_1",
        "status": "completed",
        "files": {
            "knowledge_space.json": {...},
            "implications.json": {...},
            "llm_item_classifications.json": {...},
            ...
        }
    }
    ```
    """
    
    if task_id not in _active_analyses:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found"
        )
    
    analysis = _active_analyses[task_id]
    
    if analysis["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Analysis not completed yet. Current status: {analysis['status']}"
        )
    
    # Učitaj sve JSON fajlove iz output/
    results = {}
    output_dir = Path(settings.STORAGE_PATH)
    
    if output_dir.exists():
        for file in output_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    results[file.name] = json.load(f)
            except:
                # Ako je fajl prevelik, samo napiši da postoji
                results[file.name] = {"_large_file": True, "path": file.as_posix()}
    
    return {
        "task_id": task_id,
        "status": analysis["status"],
        "completed_at": analysis["completed_at"],
        "files": results
    }


@router.get("/{task_id}/statistics")
async def get_analysis_statistics(task_id: str):
    """
    Preuzmi statističke brojeve iz analize
    
    Rezultat:
    ```json
    {
        "task_id": "analysis_1",
        "statistics": {
            "total_items": 121,
            "total_concepts": 25,
            "total_students": 692,
            "knowledge_space_states": 355,
            "prerequisites_found": 30,
            "semantic_clusters": 24,
            "root_concepts": 8
        }
    }
    ```
    """
    
    if task_id not in _active_analyses:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found"
        )
    
    analysis = _active_analyses[task_id]
    
    if analysis["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail="Analysis not completed yet"
        )
    
    # Očitaj statistiku iz output fajlova
    stats = {
        "total_items": 0,
        "total_concepts": 0,
        "total_students": 0,
        "knowledge_space_states": 0,
        "prerequisites_found": 0,
        "semantic_clusters": 0,
        "root_concepts": 0,
        "difficulty_range": {"min": None, "max": None},
        "concepts_sorted_items": 0
    }
    
    output_dir = Path(settings.STORAGE_PATH)
    
    try:
        # Knowledge space
        ks_file = output_dir / "knowledge_space.json"
        if ks_file.exists():
            with open(ks_file, 'r') as f:
                ks = json.load(f)
                stats["knowledge_space_states"] = len(ks)
        
        # Implications (prerequisites)
        impl_file = output_dir / "implications.json"
        if impl_file.exists():
            with open(impl_file, 'r') as f:
                impl = json.load(f)
                stats["prerequisites_found"] = len(impl)
        
        # LLM classifications
        llm_file = output_dir / "llm_item_classifications.json"
        if llm_file.exists():
            with open(llm_file, 'r') as f:
                llm = json.load(f)
                stats["total_items"] = len(llm)
                stats["total_concepts"] = len(set(llm.values()))
        
        # Semantic clusters
        sem_file = output_dir / "semantic_clusters.json"
        if sem_file.exists():
            with open(sem_file, 'r') as f:
                sem = json.load(f)
                stats["semantic_clusters"] = len(sem)
        
        # Item difficulties
        diff_file = output_dir / "item_difficulties.json"
        if diff_file.exists():
            with open(diff_file, 'r') as f:
                diff = json.load(f)
                difficulties = list(diff.values())
                if difficulties:
                    stats["difficulty_range"]["min"] = min(difficulties)
                    stats["difficulty_range"]["max"] = max(difficulties)
        
        # Concepts sorted by difficulty
        sorted_file = output_dir / "concepts_sorted_by_difficulty.json"
        if sorted_file.exists():
            with open(sorted_file, 'r') as f:
                sorted_concepts = json.load(f)
                stats["concepts_sorted_items"] = len(sorted_concepts)
        
        # Aggregated concepts (student count)
        agg_file = output_dir / "aggregated_concepts.csv"
        if agg_file.exists():
            with open(agg_file, 'r') as f:
                lines = f.readlines()
                if len(lines) > 1:
                    stats["total_students"] = len(lines) - 1  # -1 za header
        
        # Root concepts
        root_file = output_dir / "root_concepts.json"
        if root_file.exists():
            with open(root_file, 'r') as f:
                roots = json.load(f)
                stats["root_concepts"] = len(roots) if isinstance(roots, list) else len(roots.keys())
    
    except Exception as e:
        print(f"Error reading statistics: {e}")
    
    return {
        "task_id": task_id,
        "status": analysis["status"],
        "statistics": stats
    }


@router.get("/{task_id}/visualization")
async def get_analysis_visualization(task_id: str):
    """
    Preuzmi PNG vizuelizaciju knowledge space-a
    
    Vraća:
    - knowledge_structure_graph.png ako postoji
    - Ili info da fajl nije generiše
    """
    
    if task_id not in _active_analyses:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found"
        )
    
    analysis = _active_analyses[task_id]
    
    if analysis["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail="Analysis not completed yet"
        )
    
    output_dir = Path(settings.STORAGE_PATH)
    png_file = output_dir / "knowledge_structure_graph.png"
    
    if not png_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Visualization not found. Graph generation may have failed."
        )
    
    return {
        "task_id": task_id,
        "graph_file": png_file.as_posix(),
        "graph_exists": True
    }


@router.get("/{task_id}/files")
async def list_result_files(task_id: str):
    """
    Lista svi dostupni fajlovi iz analize
    """
    
    if task_id not in _active_analyses:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found"
        )
    
    analysis = _active_analyses[task_id]
    
    if analysis["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail="Analysis not completed yet"
        )
    
    output_dir = Path(settings.STORAGE_PATH)
    files = []
    
    if output_dir.exists():
        for file in sorted(output_dir.glob("*")):
            if file.is_file():
                files.append({
                    "name": file.name,
                    "size": file.stat().st_size,
                    "path": file.as_posix()
                })
    
    return {
        "task_id": task_id,
        "total_files": len(files),
        "files": files
    }
