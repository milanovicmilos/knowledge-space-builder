"""
Analysis Endpoints - Most između Frontend-a i Learning Space Generator-a

Backend čuva sve u PostgreSQL i komunicira sa LSG preko Celery tasks-a.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc
from rdflib import Graph, Namespace, URIRef, RDFS

from app.config import settings
from app.database import get_db
from app.models.upload import Upload
from app.models.task import Task
from app.models.result import Result
from app.celery_app.tasks import run_learning_space_generator

router = APIRouter()
logger = logging.getLogger(__name__)

SOTIS_NAMESPACE = "http://www.sotis-conference.org/ontology#"
SOTIS = Namespace(SOTIS_NAMESPACE)


def _load_sotis_graph(task_id: int, db: Session) -> tuple[Graph, Result]:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="Analysis not completed yet")

    result = db.query(Result).filter(Result.task_id == task_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Results not found")

    if not result.result_files or "sotis_ontology.ttl" not in result.result_files:
        raise HTTPException(status_code=404, detail="Ontology file not found")

    ttl_path = Path(result.result_files["sotis_ontology.ttl"])
    if not ttl_path.exists():
        raise HTTPException(status_code=404, detail=f"Ontology file not found on disk: {ttl_path}")

    graph = Graph()
    graph.parse(str(ttl_path), format="turtle")
    return graph, result


def _concept_uri(goal_id: str) -> URIRef:
    if goal_id.startswith("http://") or goal_id.startswith("https://"):
        return URIRef(goal_id)
    if not goal_id.startswith("Concept_"):
        goal_id = f"Concept_{goal_id}"
    return SOTIS[goal_id]


def _concept_id_from_uri(uri: URIRef) -> str:
    uri_str = str(uri)
    if "#" in uri_str:
        return uri_str.split("#", 1)[1]
    return uri_str.rsplit("/", 1)[-1]


def _compute_concept_difficulty(
    semantic_clusters: dict,
    item_difficulties: dict
) -> dict[str, float]:
    concept_difficulty: dict[str, float] = {}
    if not semantic_clusters or not item_difficulties:
        return concept_difficulty

    for cluster_id, items in semantic_clusters.items():
        diffs = [item_difficulties.get(item) for item in items if item in item_difficulties]
        if diffs:
            concept_difficulty[f"Concept_{cluster_id}"] = sum(diffs) / len(diffs)
    return concept_difficulty


def _compute_edge_weights(
    semantic_clusters: dict,
    implications: list[dict]
) -> dict[tuple[str, str], int]:
    if not semantic_clusters or not implications:
        return {}

    item_to_cluster = {}
    for cluster_id, items in semantic_clusters.items():
        for item in items:
            item_to_cluster[item] = cluster_id

    counts: dict[tuple[str, str], int] = {}
    for edge in implications:
        src_item = edge.get("source")
        dst_item = edge.get("target")
        if not src_item or not dst_item:
            continue
        if src_item not in item_to_cluster or dst_item not in item_to_cluster:
            continue
        src_cluster = item_to_cluster[src_item]
        dst_cluster = item_to_cluster[dst_item]
        if src_cluster == dst_cluster:
            continue
        key = (f"Concept_{src_cluster}", f"Concept_{dst_cluster}")
        counts[key] = counts.get(key, 0) + 1

    return counts


@router.post("/run")
async def run_analysis(
    file: UploadFile = File(...),
    pdf_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Pokreni novu analizu
    
    Workflow:
    1. Sačuvaj CSV (i opciono PDF) u storage/uploads/
    2. Kreiraj Upload zapis u bazi
    3. Kreiraj Task zapis u bazi
    4. Pokreni Celery task (asinhrono)
    5. Vrati task_id klijentu
    """
    
    # Validacija
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are allowed"
        )

    if pdf_file and (not pdf_file.filename or not pdf_file.filename.lower().endswith('.pdf')):
        raise HTTPException(
            status_code=400,
            detail="PDF file must have .pdf extension"
        )
    
    # Sačuvaj datoteku
    upload_dir = Path(settings.UPLOAD_PATH)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"{timestamp}_{file.filename}"
    csv_path = upload_dir / csv_filename
    pdf_path = None
    
    try:
        content = await file.read()
        with open(csv_path, "wb") as f:
            f.write(content)

        if pdf_file:
            pdf_filename = f"{timestamp}_{pdf_file.filename}"
            pdf_path = upload_dir / pdf_filename
            pdf_content = await pdf_file.read()
            with open(pdf_path, "wb") as f:
                f.write(pdf_content)
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
            parameters={
                "pdf_original_filename": pdf_file.filename if pdf_file else None
            }
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # Pokreni Celery task (asinhrono)
        celery_task = run_learning_space_generator.delay(
            task_id=task.id,
            upload_id=upload.id,
            csv_path=str(csv_path),
            pdf_path=str(pdf_path) if pdf_path else None
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


@router.get("/{task_id}/goals")
async def get_semantic_goals(task_id: int, db: Session = Depends(get_db)):
    """
    List all learning goals with labels and item counts.
    """

    graph, _ = _load_sotis_graph(task_id, db)

    query = """
        SELECT ?goal ?label (COUNT(DISTINCT ?item) AS ?itemCount)
        WHERE {
            ?goal a sotis:LearningGoal ;
                        rdfs:label ?label .
            OPTIONAL {
                ?item a sotis:LearningObject ;
                            sotis:achievesGoal ?goal .
            }
        }
        GROUP BY ?goal ?label
        ORDER BY LCASE(STR(?label))
    """

    results = graph.query(query, initNs={"sotis": SOTIS, "rdfs": RDFS})
    goals = []
    for row in results:
        concept_uri = row.goal
        goals.append({
            "id": _concept_id_from_uri(concept_uri),
            "uri": str(concept_uri),
            "label": str(row.label),
            "item_count": int(row.itemCount) if row.itemCount is not None else 0,
        })

    return {
        "goals": goals,
        "total_count": len(goals)
    }


@router.get("/{task_id}/goal-path")
async def get_goal_path(
    task_id: int,
    goal_id: str = Query(..., description="Goal ID (e.g., Concept_6 or 6) or full URI"),
    known: str | None = Query(None, description="Comma-separated concept IDs or URIs already mastered"),
    db: Session = Depends(get_db),
):
    """
    Build a learning path toward a selected goal based on ontology prerequisites.
    """

    graph, result = _load_sotis_graph(task_id, db)
    goal_uri = _concept_uri(goal_id)

    known_set: set[URIRef] = set()
    if known:
        for raw_id in known.split(","):
            raw_id = raw_id.strip()
            if raw_id:
                known_set.add(_concept_uri(raw_id))

    # Load all goal labels
    concept_labels: dict[URIRef, str] = {}
    label_query = """
    SELECT ?goal ?label
    WHERE { ?goal a sotis:LearningGoal ; rdfs:label ?label . }
    """
    for row in graph.query(label_query, initNs={"sotis": SOTIS, "rdfs": RDFS}):
        concept_labels[row.goal] = str(row.label)

    if goal_uri not in concept_labels:
        raise HTTPException(status_code=404, detail="Goal not found in ontology")

    # Load prerequisite edges (normalize to prereq -> goal direction)
    edge_query = """
    SELECT ?src ?dst
        WHERE {
            { ?src sotis:prerequisiteOf ?dst . }
            UNION
            { ?dst sotis:hasPrerequisite ?src . }
        }
    """
    edges: list[tuple[URIRef, URIRef]] = []
    forward: dict[URIRef, set[URIRef]] = {}
    reverse: dict[URIRef, set[URIRef]] = {}
    for row in graph.query(edge_query, initNs={"sotis": SOTIS}):
        src = row.src
        dst = row.dst
        edges.append((src, dst))
        forward.setdefault(src, set()).add(dst)
        reverse.setdefault(dst, set()).add(src)

    semantic_clusters = result.semantic_clusters_data or {}
    item_difficulties = result.item_difficulties or {}
    concept_difficulty = _compute_concept_difficulty(semantic_clusters, item_difficulties)
    edge_weights = _compute_edge_weights(semantic_clusters, result.implications or [])

    # Collect prerequisites for the goal
    required: set[URIRef] = set()
    stack = [goal_uri]
    while stack:
        current = stack.pop()
        if current in required:
            continue
        required.add(current)
        for prereq in reverse.get(current, set()):
            stack.append(prereq)

    if goal_uri in known_set:
        return {
            "goal": {
                "id": _concept_id_from_uri(goal_uri),
                "uri": str(goal_uri),
                "label": concept_labels.get(goal_uri, _concept_id_from_uri(goal_uri)),
                "is_known": True,
            },
            "known": [_concept_id_from_uri(uri) for uri in known_set],
            "steps": [],
            "total_steps": 0
        }

    # Remove known concepts from path (treated as satisfied)
    path_nodes = required - known_set

    # Build subgraph and topologically sort
    indegree: dict[URIRef, int] = {node: 0 for node in path_nodes}
    adjacency: dict[URIRef, set[URIRef]] = {node: set() for node in path_nodes}

    for src, dst in edges:
        if src in path_nodes and dst in path_nodes:
            adjacency[src].add(dst)
            indegree[dst] += 1

    # Depth in the prerequisite subgraph (longest path from roots)
    depth_cache: dict[URIRef, int] = {}
    MAX_DEPTH = 100  # Safeguard against infinite recursion from cycles
    
    def node_depth(node: URIRef, visited: set[URIRef] | None = None, current_depth: int = 0) -> int:
        if node in depth_cache:
            return depth_cache[node]
        
        # Safeguard: prevent infinite recursion
        if current_depth > MAX_DEPTH:
            logger.warning(f"Max depth reached for node {node}, stopping recursion")
            depth_cache[node] = MAX_DEPTH
            return MAX_DEPTH
        
        if visited is None:
            visited = set()
        
        # Detect cycles: if node already in current path, stop
        if node in visited:
            logger.warning(f"Cycle detected at node {node}, stopping recursion")
            depth_cache[node] = current_depth
            return current_depth
        
        parents = [p for p in reverse.get(node, set()) if p in path_nodes]
        if not parents:
            depth_cache[node] = 0
            return 0
        
        visited_copy = visited.copy()
        visited_copy.add(node)
        
        max_parent_depth = max(node_depth(p, visited_copy, current_depth + 1) for p in parents)
        depth_cache[node] = 1 + max_parent_depth
        return depth_cache[node]

    # FIXME: Ispravljen redosled - direktno sortiranje po depth
    # Problem: Originalni Kahn sa dinamičkim sortiranjem ne respektuje depth redosled
    
    def concept_sort_key(node: URIRef) -> tuple[int, float, str]:
        """Sortira po: (1) depth, (2) avg_difficulty, (3) label"""
        concept_id = _concept_id_from_uri(node)
        depth = node_depth(node)
        avg_diff = concept_difficulty.get(concept_id, 0.5)
        label = concept_labels.get(node, concept_id)
        # depth: od manjeg ka većem (0, 1, 2, ...)
        # avg_diff: od manjeg ka većem (lakše ka težem)
        # label: abecedno
        return (depth, avg_diff, label.lower())

    # Prvo izračunaj depth za sve čvorove
    for node in path_nodes:
        _ = node_depth(node)  # Cache-uj sve depth vrednosti
    
    # Sortiraj sve čvorove direktno
    ordered = sorted(path_nodes, key=concept_sort_key)
    
    # Validacija: proveri da prerequisiti dolaze PRE svoje consequence
    satisfied = set()
    for node in ordered:
        for prereq in reverse.get(node, set()):
            if prereq in path_nodes:
                if prereq not in satisfied:
                    # 🔴 Prerequisit dolazi POSLE - logika je pogrešna!
                    logger.error(f"Prerequisit {prereq} dolazi POSLE {node}!")
        satisfied.add(node)
    
    # Ako ima tema sa logičkim greškama (ciklusi), primeni Kahn sa popravkom
    validity_check = all(
        all(prereq in satisfied for prereq in reverse.get(node, set()) if prereq in path_nodes)
        for node in ordered
    )
    
    if not validity_check:
        logger.warning("Detected topological inconsistency, applying Kahn algorithm with fixed ordering")
        # Fallback: Kahn sa bolje kontrolom redosleda
        indegree_kahn: dict[URIRef, int] = {node: 0 for node in path_nodes}
        adjacency_kahn: dict[URIRef, set[URIRef]] = {node: set() for node in path_nodes}
        for src, dst in edges:
            if src in path_nodes and dst in path_nodes:
                adjacency_kahn[src].add(dst)
                indegree_kahn[dst] += 1
        
        # Početni queue - sortiraj odmah
        queue = sorted([node for node, degree in indegree_kahn.items() if degree == 0], 
                       key=concept_sort_key)
        ordered = []
        while queue:
            # Sortiraj queue PRE nego što uzimaš element
            queue.sort(key=concept_sort_key)
            node = queue.pop(0)
            ordered.append(node)
            
            # Dodaj sve čvorove čiji prerequisiti su sada zadovoljeni
            new_nodes = []
            for nxt in adjacency_kahn.get(node, set()):
                indegree_kahn[nxt] -= 1
                if indegree_kahn[nxt] == 0:
                    new_nodes.append(nxt)
            queue.extend(new_nodes)

    item_difficulties = result.item_difficulties or {}

    steps = []
    for concept_uri in ordered:
        item_query = """
                SELECT DISTINCT ?item ?label ?comment ?fullText
                WHERE {
                    { ?item a sotis:LearningObject ; sotis:achievesGoal ?concept . }
                    UNION
                    { ?item a sotis:Item ; sotis:belongsTo ?concept . }
                    ?item rdfs:label ?label .
                    OPTIONAL { ?item rdfs:comment ?comment . }
                    OPTIONAL { ?item sotis:fullText ?fullText . }
                }
        ORDER BY LCASE(STR(?label))
        """
        items = []
        for row in graph.query(
            item_query,
            initNs={"sotis": SOTIS, "rdfs": RDFS},
            initBindings={"concept": concept_uri},
        ):
            item_id = str(row.label)
            full_text = str(row.fullText) if row.fullText else None
            items.append({
                "id": item_id,
                "label": item_id,
                "description": str(row.comment) if row.comment else None,
                "full_text": full_text,
                "difficulty": item_difficulties.get(item_id)
            })

        unique_items = {}
        for item in items:
            if item["id"] not in unique_items:
                unique_items[item["id"]] = item
        items = list(unique_items.values())

        # Sort by difficulty when available
        items.sort(key=lambda item: (item["difficulty"] is None, item["difficulty"], item["label"]))

        concept_id = _concept_id_from_uri(concept_uri)
        avg_diff = concept_difficulty.get(concept_id)
        
        # Kreiraj prerequisite objekte sa ID i labelom
        prereq_uris = [p for p in reverse.get(concept_uri, set()) if p in path_nodes]
        prerequisites = [
            {
                "id": _concept_id_from_uri(p),
                "label": concept_labels.get(p, _concept_id_from_uri(p))
            }
            for p in sorted(prereq_uris, key=lambda x: concept_labels.get(x, str(x)).lower())
        ]
        
        prereq_evidence = []
        for p in prereq_uris:
            prereq_id = _concept_id_from_uri(p)
            weight = edge_weights.get((prereq_id, concept_id))
            if weight is not None:
                prereq_evidence.append({"id": prereq_id, "weight": weight})

        steps.append({
            "id": concept_id,
            "uri": str(concept_uri),
            "label": concept_labels.get(concept_uri, _concept_id_from_uri(concept_uri)),
            "item_count": len(items),
            "items": items,
            "recommended_items": items[:5],
            "depth": node_depth(concept_uri),
            "avg_difficulty": avg_diff,
            "prerequisites": prerequisites,  # Sada su objekti sa {id, label}
            "prerequisite_evidence": prereq_evidence,
        })

    return {
        "goal": {
            "id": _concept_id_from_uri(goal_uri),
            "uri": str(goal_uri),
            "label": concept_labels.get(goal_uri, _concept_id_from_uri(goal_uri)),
            "is_known": False,
        },
        "known": [_concept_id_from_uri(uri) for uri in known_set],
        "steps": steps,
        "total_steps": len(steps)
    }


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
