import React, { useEffect, useState } from 'react';
import './ProgressMonitor.css';
import analysisAPI from '../api/analysis';

interface ProgressMonitorProps {
  taskId: string;
  onComplete: () => void;
}

interface Status {
  task_id: string;
  status: string;
  progress: number;
  message: string;
  started_at: string | null;
  completed_at: string | null;
}

export const ProgressMonitor: React.FC<ProgressMonitorProps> = ({ taskId, onComplete }) => {
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const pollStatus = async () => {
      try {
        const statusData = await analysisAPI.getStatus(taskId);
        setStatus(statusData);

        if (statusData.status === 'completed') {
          onComplete();
        } else if (statusData.status === 'failed') {
          setError(statusData.message);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch status');
      }
    };

    // Pokreni odmah
    pollStatus();

    // Polling svakih 1 sekunde
    if (!status || (status.status !== 'completed' && status.status !== 'failed')) {
      const interval = setInterval(pollStatus, 1000);
      return () => clearInterval(interval);
    }
  }, [taskId, status, onComplete]);

  return (
    <div className="progress-monitor">
      <div className="progress-content">
        <h2>⏳ Analysis in Progress</h2>

        {error && <div className="error-box">{error}</div>}

        {status && (
          <>
            <div className="progress-info">
              <div className="progress-message">{status.message}</div>
              <div className="progress-percentage">{status.progress}%</div>
            </div>

            <div className="progress-bar-wrapper">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${status.progress}%` }}
                />
              </div>
            </div>

            <div className="progress-details">
              <div className="detail-row">
                <span>Status:</span>
                <span className={`status-badge status-${status.status}`}>
                  {status.status.toUpperCase()}
                </span>
              </div>
              {status.started_at && (
                <div className="detail-row">
                  <span>Started:</span>
                  <span>{new Date(status.started_at).toLocaleTimeString()}</span>
                </div>
              )}
              {status.completed_at && (
                <div className="detail-row">
                  <span>Completed:</span>
                  <span>{new Date(status.completed_at).toLocaleTimeString()}</span>
                </div>
              )}
            </div>

            <div className="analysis-stages">
              <h3>📋 Analysis Stages</h3>
              <div className="stage">
                <div className={`stage-check ${status.progress >= 10 ? 'done' : ''}`}>✓</div>
                <span>Data Preprocessing (DAE)</span>
                <div className="stage-progress">10%</div>
              </div>
              <div className="stage">
                <div className={`stage-check ${status.progress >= 20 ? 'done' : ''}`}>✓</div>
                <span>LLM Classification</span>
                <div className="stage-progress">20%</div>
              </div>
              <div className="stage">
                <div className={`stage-check ${status.progress >= 30 ? 'done' : ''}`}>✓</div>
                <span>Semantic Clustering</span>
                <div className="stage-progress">30%</div>
              </div>
              <div className="stage">
                <div className={`stage-check ${status.progress >= 40 ? 'done' : ''}`}>✓</div>
                <span>Concept Aggregation</span>
                <div className="stage-progress">40%</div>
              </div>
              <div className="stage">
                <div className={`stage-check ${status.progress >= 50 ? 'done' : ''}`}>✓</div>
                <span>Difficulty Analysis</span>
                <div className="stage-progress">50%</div>
              </div>
              <div className="stage">
                <div className={`stage-check ${status.progress >= 60 ? 'done' : ''}`}>✓</div>
                <span>IITA Extraction</span>
                <div className="stage-progress">60%</div>
              </div>
              <div className="stage">
                <div className={`stage-check ${status.progress >= 75 ? 'done' : ''}`}>✓</div>
                <span>Knowledge Space Generation</span>
                <div className="stage-progress">75%</div>
              </div>
              <div className="stage">
                <div className={`stage-check ${status.progress >= 85 ? 'done' : ''}`}>✓</div>
                <span>Visualization</span>
                <div className="stage-progress">85%</div>
              </div>
              <div className="stage">
                <div className={`stage-check ${status.progress >= 100 ? 'done' : ''}`}>✓</div>
                <span>RDF/TTL Ontology Export</span>
                <div className="stage-progress">100%</div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
