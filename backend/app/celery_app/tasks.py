import sys
import os
import time
import json
import re
import subprocess
import tempfile
from datetime import datetime
from typing import Optional, Dict, Any

# Add learning_space_generator to path
sys.path.insert(0, '/app/learning_space_generator')

from sqlalchemy.sql import func
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.task import Task as TaskModel
from app.models.upload import Upload
from app.models.result import Result
from app.services.storage import storage_service


def parse_progress_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse progress info from MIRT-VAE training and lattice construction"""
    progress = {}
    
    # MIRT-VAE training: "INFO:...model_trainer:Epoch 3/8 loss=0.1555 time=4.2s"
    epoch_match = re.search(r'Epoch\s+(\d+)/(\d+).*loss=([\d.]+)', line, re.IGNORECASE)
    if epoch_match:
        current_epoch = int(epoch_match.group(1))
        max_epochs = int(epoch_match.group(2))
        loss = float(epoch_match.group(3))
        
        progress['epoch'] = current_epoch
        progress['max_epochs'] = max_epochs
        progress['progress_percent'] = int((current_epoch / max_epochs) * 50)  # Training is 50% of work
        progress['current_loss'] = loss
        progress['stage'] = 'training'
        return progress
    
    # Prerequisite graph building: "INFO:...prerequisite_builder:Saved prerequisite JSON"
    prereq_match = re.search(r'prerequisite.*JSON', line, re.IGNORECASE)
    if prereq_match:
        progress['progress_percent'] = 55
        progress['stage'] = 'building_prerequisites'
        return progress
    
    # Empirical lattice: "INFO:...orchestrator:Empirical: 3966 frequent states from 117087 unique"
    lattice_match = re.search(r'Empirical:\s+(\d+)\s+frequent\s+states\s+from\s+(\d+)', line, re.IGNORECASE)
    if lattice_match:
        num_states = int(lattice_match.group(1))
        total_unique = int(lattice_match.group(2))
        progress['num_states'] = num_states
        progress['total_unique'] = total_unique
        progress['progress_percent'] = 70
        progress['stage'] = 'building_lattice'
        return progress
    
    # Lattice analysis: "INFO:...analyzer:Lattice analysis summary"
    analysis_match = re.search(r'Lattice analysis summary', line, re.IGNORECASE)
    if analysis_match:
        progress['progress_percent'] = 90
        progress['stage'] = 'analyzing'
        return progress
    
    return None


@celery_app.task(bind=True)
def run_algorithm_task(self, task_id: int, upload_id: int, parameters: dict):
    """Execute MIRT-VAE training + prerequisite graph + lattice construction with real-time progress"""
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
        
        # Create temporary output directory
        output_dir = tempfile.mkdtemp(prefix='lsg_output_')
        
        # ============ PHASE 1: Training ============
        train_cmd = [
            sys.executable, '-m', 'learning_space_generator.cli.main', 'train',
            '--csv', csv_path,
            '--out', output_dir,
            '--epochs', str(parameters.get('epochs', 8)),
            '--latent', str(parameters.get('latent_dim', 10)),
            '--device', parameters.get('device', 'cpu')
        ]
        
        task.progress_details = {'stage': 'training', 'phase': 1}
        db.commit()
        
        # Run training with real-time output
        process = subprocess.Popen(
            train_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        output_lines = []
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            output_lines.append(line)
            
            # Parse progress
            progress_info = parse_progress_line(line)
            if progress_info:
                task.progress_percent = progress_info.get('progress_percent', task.progress_percent)
                task.current_epoch = progress_info.get('epoch')
                task.progress_details = progress_info
                db.commit()
                
                self.update_state(state='PROGRESS', meta=progress_info)
        
        process.wait()
        if process.returncode != 0:
            raise Exception(f"Training failed: {''.join(output_lines[-20:])}")
        
        # ============ PHASE 2: Build Lattice ============
        pred_probs_path = os.path.join(output_dir, 'pred_probs.npy')
        item_cols_path = os.path.join(output_dir, 'item_cols.npy')
        
        build_cmd = [
            sys.executable, '-m', 'learning_space_generator.cli.main', 'build',
            '--pred', pred_probs_path,
            '--item_cols', item_cols_path,
            '--out', output_dir,
            '--select_k', str(parameters.get('select_k', 30)),
            '--min_support', str(parameters.get('min_support', 7)),
            '--pred_threshold', str(parameters.get('pred_threshold', 0.6)),
            '--implication_threshold', str(parameters.get('implication_threshold', 0.85)),
            '--min_known', str(parameters.get('min_known', 5))
        ]
        
        if parameters.get('force_k', False):
            build_cmd.append('--force_k')
        
        task.progress_details = {'stage': 'building_lattice', 'phase': 2}
        task.progress_percent = 50
        db.commit()
        
        # Run build with real-time output
        process = subprocess.Popen(
            build_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            output_lines.append(line)
            
            progress_info = parse_progress_line(line)
            if progress_info:
                task.progress_percent = progress_info.get('progress_percent', task.progress_percent)
                task.progress_details = progress_info
                db.commit()
                
                self.update_state(state='PROGRESS', meta=progress_info)
        
        process.wait()
        if process.returncode != 0:
            raise Exception(f"Lattice construction failed: {''.join(output_lines[-20:])}")
        
        # ============ Collect Results ============
        lattice_json_path = os.path.join(output_dir, f'knowledge_space_lattice_k{parameters.get("select_k", 30)}.json')
        summary_json_path = os.path.join(output_dir, f'knowledge_space_k{parameters.get("select_k", 30)}_summary.json')
        lattice_png_path = os.path.join(output_dir, f'knowledge_space_lattice_k{parameters.get("select_k", 30)}.png')
        
        # Read lattice JSON
        with open(lattice_json_path, 'r', encoding='utf-8') as f:
            lattice_data = json.load(f)
        
        # Read summary
        with open(summary_json_path, 'r', encoding='utf-8') as f:
            summary_data = json.load(f)
        
        # Save lattice JSON to storage
        with open(lattice_json_path, 'r', encoding='utf-8') as f:
            json_content = f.read()
        json_storage_key = storage_service.save_result(
            json_content,
            task_id,
            'knowledge_space_lattice.json'
        )
        
        # Save PNG if exists
        png_storage_key = None
        if os.path.exists(lattice_png_path):
            with open(lattice_png_path, 'rb') as f:
                png_content = f.read()
            png_storage_key = storage_service.save_result(
                png_content,
                task_id,
                'knowledge_space_lattice.png'
            )
        
        # Create result record
        db_result = Result(
            task_id=task_id,
            graph_storage_key=json_storage_key,
            num_states=summary_data.get('num_states', 0),
            num_edges=summary_data.get('num_edges', 0),
            num_relations=None,
            discrepancy=None,
            is_valid=summary_data.get('is_dag', True),
            algorithm='mirt-vae+lattice',
            final_generation=task.current_epoch,
            execution_time_seconds=int(time.time() - start_time),
            result_metadata={
                'png_key': png_storage_key,
                'summary': summary_data,
                'longest_path': summary_data.get('longest_path'),
                'weak_components': summary_data.get('weak_components')
            }
        )
        
        db.add(db_result)
        
        # Update task
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.progress_percent = 100
        task.progress_details = {'stage': 'completed', 'result_id': db_result.id}
        db.commit()
        
        # Cleanup temp directory
        import shutil
        shutil.rmtree(output_dir, ignore_errors=True)
        
        return {"result_id": db_result.id, "png_available": png_storage_key is not None}
        
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()
        raise
    finally:
        db.close()
