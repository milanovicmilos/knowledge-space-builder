import { useState } from 'react';
import { createTask } from '../api/client';
import type { Upload, TaskParameters } from '../types/api';

interface TaskFormProps {
  upload: Upload;
  onTaskCreated?: (taskId: number) => void;
}

export function TaskForm({ upload, onTaskCreated }: TaskFormProps) {
  const [useIita, setUseIita] = useState(false);
  const [iitaMaxDiff, setIitaMaxDiff] = useState(0.08);
  const [generations, setGenerations] = useState(50);
  const [patience, setPatience] = useState(20);
  const [parallel, setParallel] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);

    try {
      const parameters: TaskParameters = {
        use_iita: useIita,
        iita_max_diff: iitaMaxDiff,
        generations,
        patience,
        parallel,
        use_matrix_completion: true,
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
    <div className="task-form">
      <h2>Configure Analysis</h2>
      <p>File: {upload.filename} ({upload.num_rows} rows, {upload.num_columns} columns)</p>
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>
            <input
              type="checkbox"
              checked={useIita}
              onChange={(e) => setUseIita(e.target.checked)}
            />
            Use IITA (recommended for large datasets)
          </label>
        </div>

        {useIita ? (
          <div className="form-group">
            <label>
              IITA Max Diff:
              <input
                type="number"
                min="0.01"
                max="0.20"
                step="0.01"
                value={iitaMaxDiff}
                onChange={(e) => setIitaMaxDiff(parseFloat(e.target.value))}
              />
            </label>
          </div>
        ) : (
          <>
            <div className="form-group">
              <label>
                Generations:
                <input
                  type="number"
                  min="10"
                  max="500"
                  value={generations}
                  onChange={(e) => setGenerations(parseInt(e.target.value))}
                />
              </label>
            </div>
            <div className="form-group">
              <label>
                Patience (early stopping):
                <input
                  type="number"
                  min="5"
                  max="100"
                  value={patience}
                  onChange={(e) => setPatience(parseInt(e.target.value))}
                />
              </label>
            </div>
            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  checked={parallel}
                  onChange={(e) => setParallel(e.target.checked)}
                />
                Use parallel processing
              </label>
            </div>
          </>
        )}

        <button type="submit" disabled={creating}>
          {creating ? 'Starting...' : 'Start Analysis'}
        </button>
      </form>
      
      {error && <div className="error">{error}</div>}
    </div>
  );
}
