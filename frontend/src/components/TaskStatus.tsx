import { useEffect, useState } from 'react';
import { FiClock, FiZap, FiCheck, FiAlertCircle, FiRotateCcw, FiDownload, FiImage, FiX } from 'react-icons/fi';
import { getTask, getResult, deleteTask } from '../api/client';
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
  const [error, setError] = useState<string | null>(null);
  const [resultError, setResultError] = useState<string | null>(null);

  const handleStop = async () => {
    if (!taskId || stopping) return;
    setStopping(true);
    try {
      await deleteTask(taskId);
      // Reset local state
      setTask(null);
      setResult(null);
      setGraphData(null);
      if (onReset) onReset();
    } catch (err) {
      setError('Failed to stop task. Please retry.');
      console.error('Failed to stop task', err);
    } finally {
      setStopping(false);
    }
  };

  useEffect(() => {
    const fetchTaskStatus = async () => {
      try {
        setError(null);
        const taskData = await getTask(taskId);
        setTask(taskData);

        if (taskData.status === 'completed') {
          try {
            const resultData = await getResult(taskId);
            setResult(resultData);
            setResultError(null);
            
            try {
              const response = await fetch(`/api/v1/results/${taskId}/download`);
              if (response.ok) {
                const jsonData = await response.json();
                setGraphData(jsonData);
              } else {
                setResultError('Result file not available yet.');
              }
            } catch (err) {
              setResultError('Result file not available yet.');
              console.error('Failed to fetch graph data:', err);
            }
          } catch (err: any) {
            const statusCode = err?.response?.status;
            if (statusCode === 404) {
              setResult(null);
              setGraphData(null);
              setResultError('Result not available yet.');
            } else {
              setResultError('Failed to load result.');
              console.error('Failed to fetch result:', err);
            }
          }
        } else {
          setResult(null);
          setGraphData(null);
          setResultError(null);
        }
      } catch (err) {
        setError('Failed to load task status.');
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

  const progressPercent = task.progress_percent ?? 0;
  const isActive = task.status === 'running' || task.status === 'pending';

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
      case 'optimizing': {
        const trialLabel = details.trial !== undefined ? `Trial ${details.trial + 1}${details.max_trials ? `/${details.max_trials}` : ''}` : 'Running trials';
        const valuePart = details.trial_value !== undefined ? ` · Value: ${details.trial_value.toFixed(4)}` : '';
        return `Hyperparameter search: ${trialLabel}${valuePart}`;
      }
      case 'training':
        {
          const trialPart = details.trial !== undefined ? `Trial ${details.trial + 1}${details.max_trials ? `/${details.max_trials}` : ''} · ` : '';
          const epochPart = details.epoch ? `Epoch ${details.epoch}${details.max_epochs ? `/${details.max_epochs}` : ''}` : 'Training in progress';
          const lossPart = details.current_loss !== undefined ? ` - Loss: ${details.current_loss.toFixed(4)}` : '';
          const configPart = details.trial_config ? ` (latent=${details.trial_config.latent_dim}, k=${details.trial_config.select_k})` : '';
          return `${trialPart}${epochPart}${lossPart}${configPart}`;
        }
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
          <div className="status-actions">
            <span className={`status-chip status-${task.status}`}>{getStatusEmoji(task.status)} {task.status.toUpperCase()}</span>
              {isActive && (
              <button className="ghost-btn danger" onClick={handleStop} disabled={stopping}>
                <FiX size={14} style={{ marginRight: '0.35rem' }} /> {stopping ? 'Stopping...' : 'Stop task'}
              </button>
            )}
          </div>
        </div>

          {error && (
            <div className="error-banner">{error}</div>
          )}

        <div className="progress-wrapper">
          <div className="progress">
              <div className="progress-fill" style={{ width: `${progressPercent}%` }} />
          </div>
          <div className="progress-meta">
            <span className="progress-label">Progress</span>
              <strong>{progressPercent}%</strong>
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
              {task.progress_details?.stage === 'optimizing' ? (
                <>
                  {task.progress_details?.trial !== undefined && (
                    <div className="metric">
                      <p className="label">Trial</p>
                      <strong>{task.progress_details.trial + 1}</strong>
                    </div>
                  )}
                  {task.progress_details?.max_trials && (
                    <div className="metric">
                      <p className="label">Total trials</p>
                      <strong>{task.progress_details.max_trials}</strong>
                    </div>
                  )}
                  {task.progress_details?.trial_value !== undefined && (
                    <div className="metric">
                      <p className="label">Trial value</p>
                      <strong>{task.progress_details.trial_value.toFixed(4)}</strong>
                    </div>
                  )}
                </>
              ) : (
                <>
                  {task.progress_details?.trial !== undefined && (
                    <div className="metric">
                      <p className="label">Trial</p>
                      <strong>{task.progress_details.trial + 1}{task.progress_details.max_trials ? `/${task.progress_details.max_trials}` : ''}</strong>
                    </div>
                  )}
                  {task.progress_details?.epoch && (
                    <div className="metric">
                      <p className="label">Epoch</p>
                      <strong>{task.progress_details.epoch}{task.progress_details.max_epochs ? `/${task.progress_details.max_epochs}` : ''}</strong>
                    </div>
                  )}
                  {task.progress_details?.current_loss !== undefined && (
                    <div className="metric">
                      <p className="label">Loss</p>
                      <strong>{task.progress_details.current_loss.toFixed(4)}</strong>
                    </div>
                  )}
                  {task.progress_details?.trial_config?.latent_dim && (
                    <div className="metric">
                      <p className="label">Latent dim</p>
                      <strong>{task.progress_details.trial_config.latent_dim}</strong>
                    </div>
                  )}
                  {task.progress_details?.trial_config?.select_k && (
                    <div className="metric">
                      <p className="label">Select K</p>
                      <strong>{task.progress_details.trial_config.select_k}</strong>
                    </div>
                  )}
                  {task.progress_details?.trial_config?.pred_threshold && (
                    <div className="metric">
                      <p className="label">Pred threshold</p>
                      <strong>{task.progress_details.trial_config.pred_threshold.toFixed(2)}</strong>
                    </div>
                  )}
                  {task.progress_details?.num_states && (
                    <div className="metric">
                      <p className="label">States</p>
                      <strong>{task.progress_details.num_states}</strong>
                    </div>
                  )}
                </>
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

            {resultError && (
              <div className="error-banner">{resultError}</div>
            )}

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
                <p className="label">Final epoch</p>
                <strong>{result.final_generation}</strong>
              </div>
            )}
          </div>

          <div className="download-grid">
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
