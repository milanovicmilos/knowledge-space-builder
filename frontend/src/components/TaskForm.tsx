import { useState } from 'react';
import { FiZap, FiSettings } from 'react-icons/fi';
import { createTask } from '../api/client';
import type { Upload, TaskParameters } from '../types/api';
import './TaskForm.css';

interface TaskFormProps {
  upload: Upload;
  onTaskCreated?: (taskId: number) => void;
}

export function TaskForm({ upload, onTaskCreated }: TaskFormProps) {
  // Mode selection
  const [mode, setMode] = useState<'optimize' | 'manual'>('optimize');
  const [nTrials, setNTrials] = useState(10);

  // Manual parameters
  const [epochs, setEpochs] = useState(100);
  const [latentDim, setLatentDim] = useState(5);
  const [device, setDevice] = useState('cpu');
  
  // Prerequisite graph options
  const [predThreshold, setPredThreshold] = useState(0.6);
  const [implicationThreshold, setImplicationThreshold] = useState(0.85);
  const [minKnown, setMinKnown] = useState(5);
  
  // Lattice construction options
  const [selectK, setSelectK] = useState(5);
  const [minSupport, setMinSupport] = useState(3);
  const [forceK, setForceK] = useState(false);
  
  // Output options
  const [generatePng, setGeneratePng] = useState(true);
  
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);

    try {
      let parameters: TaskParameters;
      
      if (mode === 'optimize') {
        parameters = { 
            mode: 'optimize', 
            n_trials: nTrials 
        };
      } else {
        parameters = {
            mode: 'manual',
            epochs,
            latent_dim: latentDim,
            device,
            pred_threshold: predThreshold,
            implication_threshold: implicationThreshold,
            min_known: minKnown,
            select_k: selectK,
            min_support: minSupport,
            force_k: forceK,
            generate_png: generatePng,
        };
      }

      const task = await createTask(upload.id, parameters);
      onTaskCreated?.(task.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create task');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="panel task-card">
      <div className="panel-head">
        <div>
          <p className="kicker">Step 2 · Configuration</p>
          <h3>Configure Learning Space Generator</h3>
          <p className="hint">
            {mode === 'optimize' 
              ? 'Automated hyperparameter optimization and lattice construction.' 
              : 'Manual configuration of MIRT-VAE and Lattice parameters.'}
          </p>
        </div>
        <div className="pill">
          {(() => {
            const rows = upload.num_rows ?? null;
            const cols = upload.num_columns ?? null;
            const rowsText = rows === null ? 'N/A' : `${rows.toLocaleString()} ${rows === 1 ? 'row' : 'rows'}`;
            const colsText = cols === null ? 'N/A' : `${cols} ${cols === 1 ? 'column' : 'columns'}`;
            return `${rowsText} · ${colsText}`;
          })()}
        </div>
      </div>

      <div className="mode-switch">
        <button 
            type="button" 
            className={mode === 'optimize' ? 'active' : ''} 
            onClick={() => setMode('optimize')}
        >
            <FiZap /> Optimized Run
        </button>
        <button 
            type="button" 
            className={mode === 'manual' ? 'active' : ''} 
            onClick={() => setMode('manual')}
        >
            <FiSettings /> Manual Config
        </button>
      </div>

      <form className="task-form" onSubmit={handleSubmit}>
        {mode === 'optimize' ? (
            <div className="section">
                <div className="section-title">
                    <p className="kicker">Optimization Strategy</p>
                    <h4>Hyperparameter Tuning</h4>
                </div>
                <div className="field-grid">
                    <label className="field">
                        <span>Search Trials</span>
                        <input
                            type="number"
                            min="1"
                            max="50"
                            value={nTrials}
                            onChange={(e) => setNTrials(parseInt(e.target.value))}
                        />
                        <small>Number of hyperparameter combinations to evaluate.</small>
                    </label>
                    <div className="info-box" style={{ padding: '1rem', background: 'rgba(57, 163, 108, 0.1)', borderRadius: '8px' }}>
                        <p style={{ margin: 0, fontSize: '0.9rem' }}>
                            The system will automatically find the best latent dimension, training epochs, and thresholds to maximize reconstruction accuracy and lattice quality.
                        </p>
                    </div>
                </div>
            </div>
        ) : (
            <>
        <div className="section">
          <div className="section-title">
            <p className="kicker">Phase 1: MIRT-VAE Training</p>
            <h4>Neural network training parameters</h4>
            <p className="hint">Multidimensional Item Response Theory Variational Autoencoder</p>
          </div>
          <div className="field-grid">
            <label className="field">
              <span>Training epochs</span>
              <input
                type="number"
                min="1"
                max="50"
                value={epochs}
                onChange={(e) => setEpochs(parseInt(e.target.value))}
              />
              <small>Number of complete passes through the training data (recommended: 8-15).</small>
            </label>

            <label className="field">
              <span>Latent dimension</span>
              <input
                type="number"
                min="2"
                max="50"
                value={latentDim}
                onChange={(e) => setLatentDim(parseInt(e.target.value))}
              />
              <small>Size of the latent representation space (recommended: 10).</small>
            </label>

            <label className="field">
              <span>Computation device</span>
              <select value={device} onChange={(e) => setDevice(e.target.value)}>
                <option value="cpu">CPU</option>
                <option value="cuda">GPU (CUDA)</option>
              </select>
              <small>CPU is reliable; GPU requires CUDA support.</small>
            </label>
          </div>
        </div>

        <div className="section">
          <div className="section-title">
            <p className="kicker">Phase 2: Lattice Construction</p>
            <h4>Knowledge space building parameters</h4>
          </div>
          <div className="field-grid">
            <label className="field">
              <span>Select top K items</span>
              <input
                type="number"
                min="5"
                max="120"
                value={selectK}
                onChange={(e) => setSelectK(parseInt(e.target.value))}
              />
              <small>Number of most important items to include in lattice (recommended: 30).</small>
            </label>

            <label className="field">
              <span>Minimum support</span>
              <input
                type="number"
                min="1"
                max="50"
                value={minSupport}
                onChange={(e) => setMinSupport(parseInt(e.target.value))}
              />
              <small>Minimum student count for a state to be included (5-10 for sparse data).</small>
            </label>

            <label className="field field-inline">
              <input
                type="checkbox"
                checked={forceK}
                onChange={(e) => setForceK(e.target.checked)}
              />
              <div>
                <span>Force K selection</span>
                <small>Disable safety reduction (may cause memory issues for large K).</small>
              </div>
            </label>
          </div>
        </div>

        <div className="section">
          <div className="section-title advanced-toggle" onClick={() => setShowAdvanced(!showAdvanced)}>
            <div>
              <p className="kicker">Advanced options</p>
              <h4>Prerequisite graph & thresholds</h4>
            </div>
            <span className="toggle">{showAdvanced ? 'Hide' : 'Show'}</span>
          </div>
          {showAdvanced && (
            <div className="field-grid">
              <label className="field">
                <span>Prediction threshold</span>
                <input
                  type="number"
                  min="0.1"
                  max="1.0"
                  step="0.05"
                  value={predThreshold}
                  onChange={(e) => setPredThreshold(parseFloat(e.target.value))}
                />
                <small>Threshold for binarizing predictions (0.5-0.7 recommended).</small>
              </label>

              <label className="field">
                <span>Implication threshold</span>
                <input
                  type="number"
                  min="0.5"
                  max="1.0"
                  step="0.05"
                  value={implicationThreshold}
                  onChange={(e) => setImplicationThreshold(parseFloat(e.target.value))}
                />
                <small>Threshold for prerequisite relations (0.8-0.9 recommended).</small>
              </label>

              <label className="field">
                <span>Minimum known students</span>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={minKnown}
                  onChange={(e) => setMinKnown(parseInt(e.target.value))}
                />
                <small>Minimum students who must know item B for prerequisite (5-10 for sparse data).</small>
              </label>

              <label className="field field-inline">
                <input
                  type="checkbox"
                  checked={generatePng}
                  onChange={(e) => setGeneratePng(e.target.checked)}
                />
                <div>
                  <span>Generate PNG visualization</span>
                  <small>Automatic graph export.</small>
                </div>
              </label>
            </div>
          )}
        </div>

            </>
        )}

        <div className="form-actions">
          <button type="submit" disabled={creating} className="primary-btn">
            <FiZap size={16} style={{ marginRight: '0.5rem' }} />
            {creating ? 'Running...' : (mode === 'optimize' ? 'Start Optimization' : 'Start Build')}
          </button>
        </div>
      </form>

      {error && <div className="error-banner">{error}</div>}
    </div>
  );
}
