import sys
import os
import time
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
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
    line = line.strip()
    
    # Phase 1: Optimization (Auto) or Config (Manual)
    if "Phase 1: Hyperparameter Optimization" in line:
        return {'progress_percent': 10, 'stage': 'optimizing', 'detail': 'Finding optimal hyperparameters'}
    if "Phase 1: Configuring Pipeline" in line:
        return {'progress_percent': 10, 'stage': 'configuring', 'detail': 'Configuring manual pipeline'}
    
    # Phase 2: Training
    if "Phase 2: Building Knowledge Space" in line or "Phase 2: Execution (Train & Build)" in line:
        return {'progress_percent': 50, 'stage': 'training', 'detail': 'Training model and building space'}
        
    # Phase 2: Optimization trials starting
    if "Phase 2: Optimizing remaining hyperparameters" in line or "Phase 2: Optimizing" in line or "[PROGRESS] Starting" in line:
        return {'progress_percent': 15, 'stage': 'optimizing', 'detail': 'Testing hyperparameter combinations'}
    
    # [PROGRESS] Trial starting
    trial_start_match = re.search(r'\[PROGRESS\]\s*Trial\s+(\d+)\s+starting', line)
    if trial_start_match:
        trial_num = int(trial_start_match.group(1))
        return {
            'stage': 'optimizing',
            'detail': f'Starting trial {trial_num}',
            'trial': trial_num
        }
    
    # [PROGRESS] Testing config for current trial
    config_match = re.search(r'\[PROGRESS\]\s*Testing:.*latent_dim=(\d+).*select_k=(\d+).*pred_threshold=([\d.]+)', line)
    if config_match:
        return {
            'stage': 'training',
            'detail': 'Training with selected parameters',
            'trial_config': {
                'latent_dim': int(config_match.group(1)),
                'select_k': int(config_match.group(2)),
                'pred_threshold': float(config_match.group(3))
            }
        }
    
    # [PROGRESS] Trial finished
    trial_finished_match = re.search(r'\[PROGRESS\]\s*Trial\s+(\d+)\s+finished:.*score=([\d.]+)', line)
    if trial_finished_match:
        trial_num = int(trial_finished_match.group(1))
        score = float(trial_finished_match.group(2))
        return {
            'stage': 'optimizing',
            'detail': f'Trial {trial_num} finished: score={score:.4f}',
            'trial': trial_num,
            'trial_value': score
        }
        
    # [PROGRESS] Phase 1: Testing latent dimensions
    latent_dim_match = re.search(r'\[PROGRESS\]\s*Testing\s+latent_dim=(\d+)', line)
    if latent_dim_match:
        dim = int(latent_dim_match.group(1))
        return {
            'stage': 'optimizing',
            'detail': f'Testing latent_dim={dim}',
            'progress_percent': 10
        }
    
    # [PROGRESS] Phase 1 result for latent dimension
    latent_result_match = re.search(r'\[PROGRESS\]\s*latent_dim=(\d+):.*val_loss=([\d.]+)', line)
    if latent_result_match:
        dim = int(latent_result_match.group(1))
        val_loss = float(latent_result_match.group(2))
        return {
            'stage': 'optimizing',
            'detail': f'latent_dim={dim}: val_loss={val_loss:.4f}',
            'progress_percent': 10
        }
        
    # Phase 3: Evaluation
    if "Phase 3: Quality Evaluation" in line:
        return {'progress_percent': 80, 'stage': 'evaluating', 'detail': 'Evaluating quality'}

        
    # Training progress with loss
    # Format: "Epoch 3/8 loss=0.0234 time=2.5s"
    loss_match = re.search(r'Epoch\s+(\d+)/(\d+)\s+loss=([\d.]+)', line, re.IGNORECASE)
    if loss_match:
        return {
            'epoch': int(loss_match.group(1)),
            'max_epochs': int(loss_match.group(2)),
            'current_loss': float(loss_match.group(3)),
            'stage': 'training',
            'detail': f"Epoch {loss_match.group(1)}/{loss_match.group(2)} - Loss: {float(loss_match.group(3)):.4f}"
        }
    
    # Fallback: Epoch without loss
    epoch_match = re.search(r'Epoch\s+(\d+)/(\d+)', line, re.IGNORECASE)
    if epoch_match:
        return {
            'epoch': int(epoch_match.group(1)),
            'max_epochs': int(epoch_match.group(2)),
            'stage': 'training',
            'detail': f"Epoch {epoch_match.group(1)}/{epoch_match.group(2)}"
        }
    
    if "Command full completed successfully" in line or "Command manual completed successfully" in line:
        return {'progress_percent': 99, 'stage': 'finishing', 'detail': 'Finalizing'}
        
    return None


@celery_app.task(bind=True)
def run_algorithm_task(self, task_id: int, upload_id: int, parameters: dict):
    db: Session = SessionLocal()
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Load Task
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        task.status = "running"
        task.started_at = datetime.now(timezone.utc)
        task.progress_percent = 0
        task.progress_details = {'stage': 'initializing', 'progress_percent': 0}
        db.commit()
        
        # Load Upload for CSV
        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        if not upload:
            raise ValueError(f"Upload {upload_id} not found")
            
        csv_path = storage_service.get_file_path(upload.storage_key)
        # Ensure path exists or resolve it relative to storage_path
        if not os.path.exists(csv_path):
             csv_path = str(storage_service.storage_path / upload.storage_key)
        
        # Prepare Output Dir
        output_dir = tempfile.mkdtemp(prefix=f'lsg_task_{task_id}_')
        
        # Build Command based on Mode
        mode = parameters.get('mode', 'optimize')
        max_trials = None
        
        if mode == 'manual':
            # Manual Mode: specific hyperparameters
            cmd = [
                sys.executable, '-m', 'learning_space_generator.cli.optimize', 'manual',
                '--csv', str(csv_path),
                '--out_dir', str(output_dir),
                '--epochs', str(parameters.get('epochs', 100)),
                '--latent_dim', str(parameters.get('latent_dim', 5)),
                '--select_k', str(parameters.get('select_k', 5)),
                '--pred_threshold', str(parameters.get('pred_threshold', 0.6)),
                '--implication_threshold', str(parameters.get('implication_threshold', 0.85)),
                '--min_support', str(parameters.get('min_support', 5)),
                '--min_known', str(parameters.get('min_known', 2))
            ]
        else:
            # Optimize Mode (Default)
            max_trials = int(parameters.get('n_trials', 3))
            cmd = [
                sys.executable, '-m', 'learning_space_generator.cli.optimize', 'full',
                '--csv', str(csv_path),
                '--out_dir', str(output_dir),
                '--n_trials', str(max_trials)
            ]
        
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding='utf-8',
            bufsize=1,
            env={**os.environ, 'PYTHONUNBUFFERED': '1', 'PYTHONPATH': '/app'}
        )
        
        output_log = []
        current_trial = None
        current_trial_config = None
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                output_log.append(line)
                # Log all lines to see what's coming through
                logger.info(f"[STDOUT] {line.strip()}")
                parsed = parse_progress_line(line)
                if parsed:
                    # Track current trial
                    if parsed.get('trial') is not None:
                        current_trial = parsed['trial']
                        if max_trials:
                            parsed['max_trials'] = max_trials
                            trial_progress = 10 + int(((parsed['trial'] + 1) / max_trials) * 40)
                            task.progress_percent = max(task.progress_percent or 0, min(trial_progress, 50))
                    # Track trial config
                    elif parsed.get('trial_config'):
                        current_trial_config = parsed['trial_config']
                    # Inject trial context into training stage
                    elif parsed.get('stage') == 'training' and current_trial is not None:
                        parsed['trial'] = current_trial
                        if max_trials:
                            parsed['max_trials'] = max_trials
                        if current_trial_config:
                            parsed['trial_config'] = current_trial_config
                    task.progress_details = parsed
                    if parsed.get('progress_percent'):
                        task.progress_percent = parsed['progress_percent']
                    if parsed.get('epoch'):
                        task.current_epoch = parsed['epoch']
                    db.commit()
                    self.update_state(state='PROGRESS', meta=parsed)
        
        if process.returncode != 0:
            raise Exception(f"Optimization failed. Last logs: {''.join(output_log[-20:])}")

        # Collect Results
        # 1. Quality Report
        quality_report_path = os.path.join(output_dir, "quality_report.json")
        if not os.path.exists(quality_report_path):
            raise Exception("quality_report.json missing")
            
        with open(quality_report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
            
        # 2. Lattice JSON
        # Scan for lattice file
        lattice_files = [f for f in os.listdir(output_dir) if f.startswith("knowledge_space_lattice")]
        if not lattice_files:
            raise Exception("Lattice file missing")
        lattice_path = os.path.join(output_dir, lattice_files[0])
        
        with open(lattice_path, 'r', encoding='utf-8') as f:
            lattice_content = f.read()
        storage_key = storage_service.save_result(lattice_content, task_id, "lattice.json")
        
        # 3. Save DB Result
        ks_metrics = report_data.get('knowledge_space_metrics', {}).get('connectivity', {})
        
        # Add extra fields to metadata since they are not in Result model
        report_data['is_valid'] = True
        report_data['algorithm'] = 'mirt-vae+optimize'
        report_data['final_generation'] = task.current_epoch

        db_result = Result(
            task_id=task_id,
            graph_storage_key=storage_key,
            num_states=ks_metrics.get('num_states', 0),
            num_edges=ks_metrics.get('num_edges', 0),
            execution_time_seconds=(datetime.now(timezone.utc) - task.started_at).seconds,
            result_metadata=report_data
        )
        db.add(db_result)
        
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)
        task.progress_percent = 100
        task.progress_details = {'stage': 'completed', 'result_id': db_result.id}
        db.commit()
        
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        task.completed_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        # Cleanup
        try:
            if 'output_dir' in locals() and os.path.exists(output_dir):
                import shutil
                shutil.rmtree(output_dir)
        except:
            pass
        db.close()
