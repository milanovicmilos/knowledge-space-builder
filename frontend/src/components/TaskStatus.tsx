import { useEffect, useState } from 'react';
import { FiClock, FiZap, FiCheck, FiAlertCircle, FiRotateCcw, FiDownload, FiImage } from 'react-icons/fi';
import { getTask, getResult } from '../api/client';
import { GraphVisualization } from './GraphVisualization';
import type { Task, Result } from '../types/api';
import './TaskStatus.css';

interface TaskStatusProps {
  taskId: number;
  onReset?: () => void;
}

export function TaskStatus({ taskId, onReset }: TaskStatusProps) {
  const [task, setTask] = useState<Task | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [graphData, setGraphData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTaskStatus = async () => {
      try {
        const taskData = await getTask(taskId);
        setTask(taskData);

        if (taskData.status === 'completed') {
          const resultData = await getResult(taskId);
          setResult(resultData);
          
          // Fetch JSON graph data
          try {
            const response = await fetch(`/api/v1/results/results/${taskId}/download`);
            if (response.ok) {
              const jsonData = await response.json();
              setGraphData(jsonData);
            }
          } catch (err) {
            console.error('Failed to fetch graph data:', err);
          }
        }
      } catch (err) {
        console.error('Failed to fetch task status:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchTaskStatus();

    // Poll every 1 second if task is running
    const interval = setInterval(() => {
      if (task?.status === 'running' || task?.status === 'pending') {
        fetchTaskStatus();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [taskId, task?.status]);

  if (loading) return <div className="loading">Loading task status...</div>;
  if (!task) return <div className="error-banner">Task not found</div>;

  const getStatusEmoji = (status: string) => {
    switch (status) {
      case 'pending': return <FiClock size={16} />;
      case 'running': return <FiZap size={16} />;
      case 'completed': return <FiCheck size={16} />;
      case 'failed': return <FiAlertCircle size={16} />;
      default: return '?';
    }
  };

  const formatTime = (seconds: number | null | undefined) => {
    if (!seconds) return 'N/A';
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const getProgressStageText = () => {
    const details = task.progress_details;
    if (!details) return 'Initializing...';
    
    switch (details.stage) {
      case 'initializing':
        return 'Preparing environment...';
      case 'matrix_completion':
        return `Matrix completion: ${details.iteration}/${details.max_iteration} (RMSE: ${details.rmse?.toFixed(4)})`;
      case 'evolution':
        return `Generation ${details.generation}${details.max_generation ? `/${details.max_generation}` : ''} - Fitness: ${details.current_fitness?.toFixed(4)}`;
      case 'analysis':
        return `Analyzing items: ${details.current_item}/${details.total_items}`;
      case 'completed':
        return 'Analysis completed!';
      default:
        return details.stage || 'Processing...';
    }
  };

  return (
    <div className="task-status">
      <div className="panel status-panel">
        <div className="status-top">
          <div>
            <p className="kicker">Step 3 · Monitoring</p>
            <h3>Task #{taskId} status</h3>
            <p className="hint">Live progress, metrics, and logs.</p>
          </div>
          <span className={`status-chip status-${task.status}`}>{getStatusEmoji(task.status)} {task.status.toUpperCase()}</span>
        </div>

        <div className="progress-wrapper">
          <div className="progress">
            <div className="progress-fill" style={{ width: `${task.progress_percent}%` }} />
          </div>
          <div className="progress-meta">
            <span className="progress-label">Progress</span>
            <strong>{task.progress_percent}%</strong>
            {task.progress_details?.eta_seconds && (
              <span className="eta">ETA: {formatTime(task.progress_details.eta_seconds)}</span>
            )}
          </div>
        </div>

        {task.status === 'running' && (
          <div className="live-panel">
            <div>
              <p className="live-title">{getProgressStageText()}</p>
              <p className="hint">Real-time iteration and fitness tracking.</p>
            </div>
            <div className="metric-grid">
              {task.progress_details?.generation && (
                <div className="metric">
                  <p className="label">Generation</p>
                  <strong>{task.progress_details.generation}</strong>
                </div>
              )}
              {task.progress_details?.current_fitness && (
                <div className="metric">
                  <p className="label">Current fitness</p>
                  <strong>{task.progress_details.current_fitness.toFixed(4)}</strong>
                </div>
              )}
              {task.progress_details?.best_fitness && (
                <div className="metric">
                  <p className="label">Best fitness</p>
                  <strong>{task.progress_details.best_fitness.toFixed(4)}</strong>
                </div>
              )}
            </div>
          </div>
        )}

        {task.error_message && (
          <div className="error-panel">
            <div className="label">Error</div>
            <pre>{task.error_message}</pre>
          </div>
        )}

        <div className="timeline">
          <div>
            <p className="label">Created</p>
            <p className="muted">{new Date(task.created_at).toLocaleString()}</p>
          </div>
          {task.started_at && (
            <div>
              <p className="label">Started</p>
              <p className="muted">{new Date(task.started_at).toLocaleString()}</p>
            </div>
          )}
          {task.completed_at && (
            <div>
              <p className="label">Completed</p>
              <p className="muted">{new Date(task.completed_at).toLocaleString()}</p>
            </div>
          )}
        </div>
      </div>

      {result && (
        <div className="panel result-panel">
          <div className="panel-head">
            <div>
              <p className="kicker">Analysis results</p>
              <h3>Graph summary</h3>
              <p className="hint">Key metrics and result export.</p>
            </div>
          </div>

          <div className="metric-grid wide">
            <div className="metric card">
              <p className="label">Algorithm</p>
              <strong>{result.algorithm.toUpperCase()}</strong>
            </div>
            {result.num_states && (
              <div className="metric card">
                <p className="label">States</p>
                <strong>{result.num_states.toLocaleString()}</strong>
              </div>
            )}
            {result.num_edges && (
              <div className="metric card">
                <p className="label">Edges</p>
                <strong>{result.num_edges.toLocaleString()}</strong>
              </div>
            )}
            {result.num_relations && (
              <div className="metric card">
                <p className="label">Relations</p>
                <strong>{result.num_relations.toLocaleString()}</strong>
              </div>
            )}
            {result.execution_time_seconds && (
              <div className="metric card">
                <p className="label">Execution time</p>
                <strong>{formatTime(result.execution_time_seconds)}</strong>
              </div>
            )}
            {result.final_generation && (
              <div className="metric card">
                <p className="label">Final generation</p>
                <strong>{result.final_generation}</strong>
              </div>
            )}
          </div>

          <div className="download-grid">
            <button className="primary-btn" onClick={() => window.location.href = `/api/v1/results/results/${taskId}/download`}>
              <FiDownload size={16} style={{ marginRight: '0.5rem' }} />
              Download JSON
            </button>
            {result.result_metadata?.png_key && (
              <button className="secondary-btn" onClick={() => window.location.href = `/api/v1/results/results/${taskId}/download?format=png`}>
                <FiImage size={16} style={{ marginRight: '0.5rem' }} />
                Download PNG
              </button>
            )}
          </div>
        </div>
      )}

      {result && graphData && (
        <GraphVisualization
          graphData={graphData}
          algorithm={result.algorithm as 'neat' | 'iita'}
        />
      )}

      {onReset && (
        <div className="inline-actions">
          <button className="ghost-btn" onClick={onReset}>
            <FiRotateCcw size={16} style={{ marginRight: '0.5rem' }} />
            Start new workflow
          </button>
        </div>
      )}
    </div>
  );
}
