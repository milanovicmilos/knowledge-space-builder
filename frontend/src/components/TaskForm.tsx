import { useState } from 'react';
import { createTask } from '../api/client';
import type { Upload, TaskParameters } from '../types/api';
import './TaskForm.css';

interface TaskFormProps {
  upload: Upload;
  onTaskCreated?: (taskId: number) => void;
}

export function TaskForm({ upload, onTaskCreated }: TaskFormProps) {
  // LSG Options
  // Default values match local config (learning_space_generator/app/core/config.py)
  const [iitaThreshold, setIitaThreshold] = useState(0.05);
  const [semanticWeight, setSemanticWeight] = useState(0.3);
  
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);

    try {
      const parameters: TaskParameters = {
        mode: 'lsg_pipeline',
        iita_threshold: iitaThreshold,
        semantic_weight: semanticWeight
      };

      const task = await createTask(upload.id, parameters);
      onTaskCreated?.(task.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create task');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className='panel task-card'>
      <div className='panel-head'>
        <div>
          <p className='kicker'>Step 2  Configuration</p>
          <h3>Construct Knowledge Space</h3>
          <p className='hint'>
             Run the SOTIS 2026 Pipeline (IITA + Semantic Analysis).
          </p>
        </div>
        <div className='pill'>
          {upload.original_filename}
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div className='form-group'>
            <label>IITA Threshold Rate</label>
            <input 
                type='number' 
                step='0.01' 
                min='0.01' 
                max='1.0' 
                value={iitaThreshold} 
                onChange={e => setIitaThreshold(parseFloat(e.target.value))}
            />
            <small>Threshold for accepting implications (lower = looser).</small>
        </div>

        <div className='form-group'>
            <label>Semantic Weight (Lambda)</label>
            <input 
                type='number' 
                step='0.01' 
                min='0.0' 
                max='1.0' 
                value={semanticWeight} 
                onChange={e => setSemanticWeight(parseFloat(e.target.value))}
            />
            <small>Weight for LLM/Semantic similarity regularization.</small>
        </div>

        {error && <div className='error-message'>{error}</div>}

        <button type='submit' className='button primary' disabled={creating}>
          {creating ? 'Starting Pipeline...' : 'Generate Knowledge Space'}
        </button>
      </form>
    </div>
  );
}

