import { useEffect, useState } from 'react';
import { FiClock, FiZap, FiCheck, FiAlertCircle, FiRotateCcw, FiDownload, FiImage, FiX } from 'react-icons/fi';
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
  const [stopping, setStopping] = useState(false);
  const [resultError, setResultError] = useState<string | null>(null);

  const handleStopTask = async () => {
    setStopping(true);
    try {
      const response = await fetch(`/api/v1/tasks/tasks/${taskId}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error('Failed to stop task');
      }
      // Trigger reset to go back to upload
      onReset?.();
    } catch (err: any) {
      alert('Error stopping task: ' + (err.message || 'Unknown error'));
    } finally {
      setStopping(false);
    }
  };

  useEffect(() => {
    const fetchTaskStatus = async () => {
      try {
        const taskData = await getTask(taskId);
        setTask(taskData);

        if (taskData.status === 'completed') {
          setResultError(null);
          try {
            const resultData = await getResult(taskId);
            setResult(resultData);
            
            // Fetch JSON graph data
            try {
              const response = await fetch(`/api/v1/results/${taskId}/download`);
              if (response.ok) {
                const jsonData = await response.json();
                setGraphData(jsonData);
              }
            } catch (err) {
              console.error('Failed to fetch graph data:', err);
            }
          } catch (err: any) {
            setResultError(err.response?.data?.detail || 'Failed to load result. Please try again later.');
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
      case 'training':
        return `Training: Epoch ${details.epoch}${details.max_epochs ? `/${details.max_epochs}` : ''} - Loss: ${details.current_loss?.toFixed(4) || 'calculating'}`;
      case 'building_prerequisites':
        return 'Building prerequisite graph...';
      case 'building_lattice':
        return `Building lattice: ${details.num_states} states from ${details.total_unique} unique`;
      case 'analyzing':
        return 'Analyzing knowledge space...';
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
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <span className={`status-chip status-${task.status}`}>{getStatusEmoji(task.status)} {task.status.toUpperCase()}</span>
            {task.status === 'running' && (
              <button 
                className="danger-btn" 
                onClick={handleStopTask}
                disabled={stopping}
                style={{ padding: '0.4rem 0.8rem', fontSize: '0.9rem' }}
              >
                <FiX size={14} style={{ marginRight: '0.3rem' }} />
                {stopping ? 'Stopping...' : 'Stop'}
              </button>
            )}
          </div>
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
              <p className="hint">Real-time training progress and loss tracking.</p>
            </div>
            <div className="metric-grid">
              {task.progress_details?.epoch && (
                <div className="metric">
                  <p className="label">Epoch</p>
                  <strong>{task.progress_details.epoch}</strong>
                </div>
              )}
              {task.progress_details?.current_loss && (
                <div className="metric">
                  <p className="label">Current loss</p>
                  <strong>{task.progress_details.current_loss.toFixed(4)}</strong>
                </div>
              )}
              {task.progress_details?.num_states && (
                <div className="metric">
                  <p className="label">States</p>
                  <strong>{task.progress_details.num_states}</strong>
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

      {task.status === 'completed' && resultError && (
        <div className="panel error-panel">
          <div className="panel-head">
            <p className="kicker">Results</p>
            <h3>Network Error</h3>
          </div>
          <p>{resultError}</p>
        </div>
      )}

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
            {result.execution_time_seconds && (
              <div className="metric card">
                <p className="label">Execution time</p>
                <strong>{formatTime(result.execution_time_seconds)}</strong>
              </div>
            )}
          </div>

          <div className="actions">
            <button className="primary-btn" onClick={() => window.location.href = `/api/v1/results/${taskId}/download`}>
              <FiDownload size={16} style={{ marginRight: '0.5rem' }} />
              Download JSON
            </button>
            {result.result_metadata?.png_key && (
              <button className="secondary-btn" onClick={() => window.location.href = `/api/v1/results/${taskId}/download?format=png`}>
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
