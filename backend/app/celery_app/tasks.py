import sys
import os
import time
import json
from datetime import datetime

# Add learning-space-generator to path
sys.path.insert(0, '/app/learning-space-generator')

from celery import Task
from sqlalchemy.sql import func
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.task import Task as TaskModel
from app.models.upload import Upload
from app.models.result import Result
from app.services.storage import storage_service


@celery_app.task(bind=True)
def run_algorithm_task(self, task_id: int, upload_id: int, parameters: dict):
    """Execute NEAT or IITA algorithm"""
    db = SessionLocal()
    
    try:
        # Update task status
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        task.status = "running"
        task.started_at = datetime.utcnow()
        db.commit()
        
        # Get upload
        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        csv_path = storage_service.get_file_path(upload.storage_key)
        
        start_time = time.time()
        
        # Prepare arguments for LSG
        use_iita = parameters.get('use_iita', False)
        
        if use_iita:
            # Run IITA
            import tempfile
            output_json = tempfile.mktemp(suffix='.json')
            
            # Run via command line interface
            import subprocess
            cmd = [
                sys.executable, '-m', 'lsg.run',
                '--data-path', csv_path,
                '--use-iita',
                '--iita-max-diff', str(parameters.get('iita_max_diff', 0.08)),
                '--json', output_json,
                '--silent',
                '--no-cache'
            ]
            
            # Change to lsg directory
            cwd = '/app/learning-space-generator'
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"IITA failed: {result.stderr}")
            
            # Read result
            with open(output_json, 'r') as f:
                result_data = json.load(f)
            
            # Save to storage
            with open(output_json, 'r') as f:
                result_content = f.read()
            
            storage_key = storage_service.save_result(
                result_content,
                task_id,
                'learning_space.json'
            )
            
            # Parse metadata
            num_relations = result_data.get('metadata', {}).get('total_relations', 0)
            num_items = result_data.get('metadata', {}).get('n_items', 0)
            
            # Create result record
            db_result = Result(
                task_id=task_id,
                graph_storage_key=storage_key,
                num_states=None,
                num_edges=None,
                num_relations=num_relations,
                discrepancy=None,
                is_valid=None,
                algorithm='iita',
                final_generation=None,
                execution_time_seconds=int(time.time() - start_time),
                result_metadata=result_data.get('metadata', {})
            )
            
            os.unlink(output_json)
            
        else:
            # Run NEAT
            import tempfile
            output_json = tempfile.mktemp(suffix='.json')
            
            cmd = [
                sys.executable, '-m', 'lsg.run',
                '--data-path', csv_path,
                '--generations', str(parameters.get('generations', 50)),
                '--patience', str(parameters.get('patience', 20)),
                '--json', output_json,
                '--silent',
                '--no-cache'
            ]
            
            if parameters.get('parallel', True):
                cmd.append('--parallel')
            
            cwd = '/app/learning-space-generator'
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"NEAT failed: {result.stderr}")
            
            # Read result
            with open(output_json, 'r') as f:
                result_data = json.load(f)
            
            # Save to storage
            with open(output_json, 'r') as f:
                result_content = f.read()
            
            storage_key = storage_service.save_result(
                result_content,
                task_id,
                'learning_space.json'
            )
            
            # Count states and edges
            num_states = len(result_data)
            num_edges = sum(len(v) for v in result_data.values())
            
            # Create result record
            db_result = Result(
                task_id=task_id,
                graph_storage_key=storage_key,
                num_states=num_states,
                num_edges=num_edges,
                num_relations=None,
                discrepancy=None,  # Would need to parse from output
                is_valid=True,  # Assume valid if completed
                algorithm='neat',
                final_generation=parameters.get('generations', 50),
                execution_time_seconds=int(time.time() - start_time),
                result_metadata={}
            )
            
            os.unlink(output_json)
        
        db.add(db_result)
        
        # Update task
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.progress_percent = 100
        db.commit()
        
        return {"result_id": db_result.id}
        
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()
        raise
    finally:
        db.close()
