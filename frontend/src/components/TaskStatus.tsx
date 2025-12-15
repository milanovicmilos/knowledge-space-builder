import { useEffect, useState } from 'react';
import { getTask, getResult } from '../api/client';
import type { Task, Result } from '../types/api';

interface TaskStatusProps {
  taskId: number;
}

export function TaskStatus({ taskId }: TaskStatusProps) {
  const [task, setTask] = useState<Task | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTaskStatus = async () => {
      try {
        const taskData = await getTask(taskId);
        setTask(taskData);

        if (taskData.status === 'completed') {
          const resultData = await getResult(taskId);
          setResult(resultData);
        }
      } catch (err) {
        console.error('Failed to fetch task status:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchTaskStatus();

    // Poll every 2 seconds if task is running
    const interval = setInterval(() => {
      if (task?.status === 'running' || task?.status === 'pending') {
        fetchTaskStatus();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [taskId, task?.status]);

  if (loading) return <div>Loading...</div>;
  if (!task) return <div>Task not found</div>;

  return (
    <div className="task-status">
      <h2>Task Status</h2>
      <div className="status-info">
        <p><strong>Status:</strong> {task.status}</p>
        <p><strong>Progress:</strong> {task.progress_percent}%</p>
        {task.current_generation && (
          <p><strong>Generation:</strong> {task.current_generation}</p>
        )}
        {task.error_message && (
          <div className="error">Error: {task.error_message}</div>
        )}
      </div>

      {result && (
        <div className="result-info">
          <h3>Results</h3>
          <p><strong>Algorithm:</strong> {result.algorithm.toUpperCase()}</p>
          {result.num_states && <p><strong>States:</strong> {result.num_states}</p>}
          {result.num_edges && <p><strong>Edges:</strong> {result.num_edges}</p>}
          {result.num_relations && <p><strong>Relations:</strong> {result.num_relations}</p>}
          {result.execution_time_seconds && (
            <p><strong>Execution time:</strong> {result.execution_time_seconds}s</p>
          )}
          <button onClick={() => window.location.href = `/api/v1/results/results/${taskId}/download`}>
            Download JSON
          </button>
        </div>
      )}
    </div>
  );
}
