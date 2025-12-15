import sys
import os
import time
import json
import re
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any

# Add learning-space-generator to path
sys.path.insert(0, '/app/learning-space-generator')

from sqlalchemy.sql import func
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.task import Task as TaskModel
from app.models.upload import Upload
from app.models.result import Result
from app.services.storage import storage_service


def parse_progress_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse progress info from NEAT/IITA stdout"""
    progress = {}
    
    # NEAT progress: "Generation 42/100: Best fitness = 0.85, Current = 0.78"
    neat_match = re.search(r'Generation\s+(\d+)(?:/(\d+))?.*fitness.*?=\s*([\d.]+)', line, re.IGNORECASE)
    if neat_match:
        current_gen = int(neat_match.group(1))
        max_gen = int(neat_match.group(2)) if neat_match.group(2) else None
        fitness = float(neat_match.group(3))
        
        progress['generation'] = current_gen
        if max_gen:
            progress['max_generation'] = max_gen
            progress['progress_percent'] = int((current_gen / max_gen) * 100)
        progress['current_fitness'] = fitness
        progress['stage'] = 'evolution'
        return progress
    
    # IITA progress: "Processing item 45/120..."
    iita_match = re.search(r'(?:Processing|Analyzing).*?(\d+)/(\d+)', line, re.IGNORECASE)
    if iita_match:
        current = int(iita_match.group(1))
        total = int(iita_match.group(2))
        progress['current_item'] = current
        progress['total_items'] = total
        progress['progress_percent'] = int((current / total) * 100)
        progress['stage'] = 'analysis'
        return progress
    
    # Matrix completion: "Iteration 15/30: RMSE = 0.0022"
    matrix_match = re.search(r'Iteration\s+(\d+)/(\d+).*RMSE\s*=\s*([\d.]+)', line, re.IGNORECASE)
    if matrix_match:
        current_iter = int(matrix_match.group(1))
        max_iter = int(matrix_match.group(2))
        rmse = float(matrix_match.group(3))
        progress['iteration'] = current_iter
        progress['max_iteration'] = max_iter
        progress['progress_percent'] = int((current_iter / max_iter) * 30)  # Matrix is ~30% of total
        progress['rmse'] = rmse
        progress['stage'] = 'matrix_completion'
        return progress
    
    return None


@celery_app.task(bind=True)
def run_algorithm_task(self, task_id: int, upload_id: int, parameters: dict):
    """Execute NEAT or IITA algorithm with real-time progress tracking"""
    db = SessionLocal()
    
    try:
        # Update task status
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        task.status = "running"
        task.started_at = datetime.utcnow()
        task.progress_details = {'stage': 'initializing'}
        db.commit()
        
        # Get upload
        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        csv_path = storage_service.get_file_path(upload.storage_key)
        
        start_time = time.time()
        
        # Build command with all parameters
        import tempfile
        output_json = tempfile.mktemp(suffix='.json')
        png_output = tempfile.mktemp(suffix='.png') if parameters.get('generate_png', True) else None
        
        cmd = [sys.executable, '-m', 'lsg.run', '--data-path', csv_path]
        
        # Algorithm selection
        if parameters.get('use_iita', False):
            cmd.extend(['--use-iita', '--iita-max-diff', str(parameters.get('iita_max_diff', 0.08))])
            algorithm = 'iita'
        else:
            algorithm = 'neat'
            # NEAT specific options
            if parameters.get('greedy', False):
                cmd.append('--greedy')
            else:
                cmd.extend(['--generations', str(parameters.get('generations', 50))])
                cmd.extend(['--patience', str(parameters.get('patience', 20))])
            
            if parameters.get('parallel', True):
                cmd.append('--parallel')
            
            if parameters.get('plot', False):
                cmd.append('--plot')
        
        # Data options
        if parameters.get('randomize_items', False):
            cmd.append('--randomize-items')
        
        # Cache options
        if parameters.get('clear_cache', False):
            cmd.append('--clear-cache')
        cmd.append('--no-cache')  # Always use --no-cache for read-only volume
        
        # Output options
        cmd.extend(['--json', output_json])
        if png_output:
            cmd.extend(['--png', png_output])
        
        # Run process with real-time output capture
        cwd = '/app/learning-space-generator'
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Read output line by line
        output_lines = []
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            
            output_lines.append(line)
            
            # Parse progress
            progress_info = parse_progress_line(line)
            if progress_info:
                # Update task with progress
                task.progress_percent = progress_info.get('progress_percent', task.progress_percent)
                task.current_generation = progress_info.get('generation')
                task.progress_details = progress_info
                db.commit()
                
                # Update Celery task state for real-time tracking
                self.update_state(
                    state='PROGRESS',
                    meta=progress_info
                )
        
        process.wait()
        
        if process.returncode != 0:
            full_output = ''.join(output_lines)
            raise Exception(f"{algorithm.upper()} failed with exit code {process.returncode}:\n{full_output}")
        
        # Read result JSON
        with open(output_json, 'r') as f:
            result_data = json.load(f)
        
        # Save JSON to storage
        with open(output_json, 'r') as f:
            result_content = f.read()
        
        json_storage_key = storage_service.save_result(
            result_content,
            task_id,
            'learning_space.json'
        )
        
        # Save PNG if generated
        png_storage_key = None
        if png_output and os.path.exists(png_output):
            with open(png_output, 'rb') as f:
                png_content = f.read()
            png_storage_key = storage_service.save_result(
                png_content,
                task_id,
                'learning_space.png'
            )
            os.unlink(png_output)
        
        # Parse algorithm-specific metadata
        if algorithm == 'iita':
            num_relations = result_data.get('metadata', {}).get('total_relations', 0)
            num_items = result_data.get('metadata', {}).get('n_items', 0)
            
            db_result = Result(
                task_id=task_id,
                graph_storage_key=json_storage_key,
                num_states=None,
                num_edges=None,
                num_relations=num_relations,
                discrepancy=None,
                is_valid=None,
                algorithm='iita',
                final_generation=None,
                execution_time_seconds=int(time.time() - start_time),
                result_metadata={'png_key': png_storage_key, **result_data.get('metadata', {})}
            )
        else:  # NEAT
            num_states = len(result_data) if isinstance(result_data, dict) else 0
            num_edges = sum(len(v) for v in result_data.values()) if isinstance(result_data, dict) else 0
            
            db_result = Result(
                task_id=task_id,
                graph_storage_key=json_storage_key,
                num_states=num_states,
                num_edges=num_edges,
                num_relations=None,
                discrepancy=None,
                is_valid=True,
                algorithm='neat',
                final_generation=task.current_generation,
                execution_time_seconds=int(time.time() - start_time),
                result_metadata={'png_key': png_storage_key}
            )
        
        os.unlink(output_json)
        db.add(db_result)
        
        # Update task
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.progress_percent = 100
        task.progress_details = {'stage': 'completed', 'result_id': db_result.id}
        db.commit()
        
        return {"result_id": db_result.id, "png_available": png_storage_key is not None}
        
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()
        raise
    finally:
        db.close()
