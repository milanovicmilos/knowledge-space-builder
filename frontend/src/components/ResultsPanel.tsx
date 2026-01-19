import { useEffect, useState } from 'react';
import { listResults, deleteResult } from '../api/client';
import './ResultsPanel.css';

interface ResultsPanelProps {
  onOpenTask: (taskId: number) => void;
}

export function ResultsPanel({ onOpenTask }: ResultsPanelProps) {
  const [items, setItems] = useState<Array<any>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await listResults({ limit: 25, offset: 0 });
        setItems(data.items);
      } catch (e: any) {
        setError(e?.message || 'Failed to load results');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleDelete = async (taskId: number) => {
    setDeleting(taskId);
    try {
      await deleteResult(taskId);
      setItems(items.filter(it => it.task_id !== taskId));
      setConfirmDelete(null);
    } catch (e: any) {
      setError(e?.message || 'Failed to delete result');
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="panel results-panel">
      <div className="panel-head">
        <div>
          <p className="kicker">Results</p>
          <h3>Recent analyses</h3>
          <p className="hint">Open graph, or download JSON/PNG.</p>
        </div>
      </div>

      {loading && <div className="loading">Loading results...</div>}
      {error && <div className="error-banner">{error}</div>}

      {!loading && !error && (
        <div className="results-table-wrapper">
          <table className="results-table">
            <thead>
              <tr>
                <th>Task</th>
                <th>Algorithm</th>
                <th>Status</th>
                <th>Dataset</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr key={it.result_id}>
                  <td>#{it.task_id}</td>
                  <td className="alg">{it.algorithm.toUpperCase()}</td>
                  <td><span className={`status-chip status-${it.status}`}>{it.status.toUpperCase()}</span></td>
                  <td title={it.upload_filename} className="truncate">{it.upload_filename}</td>
                  <td>{new Date(it.created_at).toLocaleString()}</td>
                  <td className="actions">
                    <button className="secondary-btn" onClick={() => onOpenTask(it.task_id)}>Open graph</button>
                    <a className="ghost-btn" href={`/api/v1/results/${it.task_id}/download`}>JSON</a>
                    {it.has_png && (
                      <a className="ghost-btn" href={`/api/v1/results/${it.task_id}/download?format=png`}>PNG</a>
                    )}
                    {it.has_ontology && (
                       <a className="ghost-btn" href={`/api/v1/results/${it.task_id}/download?format=ontology`}>TTL</a>
                    )}
                    <button 
                      className="ghost-btn delete-btn"
                      onClick={() => setConfirmDelete(it.task_id)}
                      disabled={deleting === it.task_id}
                    >
                      {deleting === it.task_id ? 'Deleting...' : 'Delete'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {confirmDelete !== null && (
        <div className="modal-overlay">
          <div className="confirmation-modal">
            <h3>Delete result?</h3>
            <p>This cannot be undone. The analysis data and files will be permanently removed.</p>
            <div className="modal-actions">
              <button 
                className="ghost-btn"
                onClick={() => setConfirmDelete(null)}
              >
                Cancel
              </button>
              <button 
                className="destructive-btn"
                onClick={() => handleDelete(confirmDelete)}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
