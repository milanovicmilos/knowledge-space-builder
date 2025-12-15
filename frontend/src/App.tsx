import { useState } from 'react';
import { UploadForm } from './components/UploadForm';
import { TaskForm } from './components/TaskForm';
import { TaskStatus } from './components/TaskStatus';
import type { Upload } from './types/api';
import './App.css';

type Stage = 'upload' | 'configure' | 'monitor';

const stageCopy: Record<Stage, { title: string; body: string; badge: string }> = {
  upload: {
    title: 'Prepare your data',
    body: 'Import CSV dataset and validate metadata before starting the analysis.',
    badge: 'Step 1/3',
  },
  configure: {
    title: 'Configure algorithm',
    body: 'Choose NEAT or IITA, fine-tune parameters and launch the construction process.',
    badge: 'Step 2/3',
  },
  monitor: {
    title: 'Monitor progress and results',
    body: 'Track live metrics, generated knowledge graph and output formats for further analysis.',
    badge: 'Step 3/3',
  },
};

function App() {
  const [currentUpload, setCurrentUpload] = useState<Upload | null>(null);
  const [currentTaskId, setCurrentTaskId] = useState<number | null>(null);

  const stage: Stage = !currentUpload
    ? 'upload'
    : currentTaskId
    ? 'monitor'
    : 'configure';

  const handleUploadComplete = (upload: Upload) => {
    setCurrentUpload(upload);
    setCurrentTaskId(null);
  };

  const handleTaskCreated = (taskId: number) => {
    setCurrentTaskId(taskId);
  };

  const handleReset = () => {
    setCurrentUpload(null);
    setCurrentTaskId(null);
  };

  const stageStatus = (s: Stage) => {
    if (stage === s) return 'active';
    if (stage === 'monitor' || (stage === 'configure' && s === 'upload')) return 'done';
    if (stage === 'configure' && s === 'monitor') return 'pending';
    return stage === 'upload' ? 'pending' : 'done';
  };

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="hero__content">
          <p className="eyebrow">Knowledge Space Construction · Research Platform</p>
          <h1>Knowledge Space Builder</h1>
          <p className="hero__lede">
            Construct and visualize knowledge spaces from empirical assessment data using NEAT and IITA algorithms.
            Focus on reliable data pipelines, comprehensive metrics and clear interpretation of results.
          </p>
          <div className="hero__tags">
            <span className="chip chip--primary">NEAT · IITA</span>
            <span className="chip">Real-time visualization</span>
            <span className="chip">Automatic PNG/JSON export</span>
          </div>
        </div>

        <div className="hero__panel">
          <div className="panel-label">Current workflow</div>
          <div className={`stage-card stage-${stage}`}>
            <div className="stage-badge">{stageCopy[stage].badge}</div>
            <h3>{stageCopy[stage].title}</h3>
            <p>{stageCopy[stage].body}</p>
            <div className="stage-steps">
              {([
                { key: 'upload' as Stage, label: 'Upload' },
                { key: 'configure' as Stage, label: 'Configure' },
                { key: 'monitor' as Stage, label: 'Monitor' }
              ]).map(({ key, label }) => (
                <div key={key} className={`stage-step ${stageStatus(key)}`}>
                  <span className="dot" />
                  <span>{label}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="panel-hint">
            <div>
              <strong>Workflow</strong>
              <p>Upload → configure algorithm → monitor → export graph.</p>
            </div>
            <button className="link-btn" onClick={handleReset}>Start new workflow</button>
          </div>
        </div>
      </header>

      <main className="main-grid">
        <section className="primary-surface">
          <div className="section-header">
            <div>
              <p className="section-kicker">Interactive workflow</p>
              <h2>{stageCopy[stage].title}</h2>
              <p className="section-sub">{stageCopy[stage].body}</p>
            </div>
            {currentUpload && (
              <div className="upload-pill">
                <span className="pill-label">Dataset</span>
                <strong>{currentUpload.filename}</strong>
                <span className="pill-meta">{currentUpload.num_rows?.toLocaleString() || 'N/A'} rows · {currentUpload.num_columns || 'N/A'} columns</span>
              </div>
            )}
          </div>

          {!currentUpload && (
            <UploadForm onUploadComplete={handleUploadComplete} />
          )}

          {currentUpload && !currentTaskId && (
            <>
              <TaskForm upload={currentUpload} onTaskCreated={handleTaskCreated} />
              <div className="inline-actions">
                <button className="ghost-btn" onClick={handleReset}>Upload different dataset</button>
              </div>
            </>
          )}

          {currentTaskId && (
            <>
              <TaskStatus taskId={currentTaskId} onReset={handleReset} />
            </>
          )}
        </section>

        <aside className="sidebar">
          <div className="sidebar-card">
            <p className="sidebar-kicker">About</p>
            <h3>Knowledge space construction</h3>
            <p>
              Apply neuroevolutionary or IITA approaches to generate relational concept graphs from empirical assessment
              data. Visualize states, connections and robustness metrics.
            </p>
            <ul className="bullet-list">
              <li>Metadata validation and matrix preparation</li>
              <li>Live evolution and heuristics tracking</li>
              <li>Export visualizations (PNG) and structures (JSON)</li>
            </ul>
          </div>

          <div className="sidebar-card">
            <p className="sidebar-kicker">Dataset requirements</p>
            <div className="badge">CSV, ; or , separator</div>
            <div className="badge">Min 50 rows</div>
            <div className="badge">Columns = items</div>
            <p className="muted">For large matrices (100+ items) prefer IITA and enable matrix completion.</p>
          </div>

          <div className="sidebar-card compact">
            <div>
              <p className="sidebar-kicker">Workflow control</p>
              <p className="muted">Reset session or change algorithm at any point.</p>
            </div>
            <button className="secondary-btn" onClick={handleReset}>New workflow</button>
          </div>
        </aside>
      </main>
    </div>
  );
}

export default App;
