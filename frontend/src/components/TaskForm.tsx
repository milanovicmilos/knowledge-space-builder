import { useState } from 'react';
import { FiZap } from 'react-icons/fi';
import { createTask } from '../api/client';
import type { Upload, TaskParameters } from '../types/api';
import './TaskForm.css';

interface TaskFormProps {
  upload: Upload;
  onTaskCreated?: (taskId: number) => void;
}

export function TaskForm({ upload, onTaskCreated }: TaskFormProps) {
  // Algorithm selection
  const [useIita, setUseIita] = useState(false);
  
  // IITA options
  const [iitaMaxDiff, setIitaMaxDiff] = useState(0.08);
  
  // NEAT options
  const [generations, setGenerations] = useState(50);
  const [patience, setPatience] = useState(20);
  const [parallel, setParallel] = useState(true);
  const [greedy, setGreedy] = useState(false);
  const [plot, setPlot] = useState(false);
  
  // Data options
  const [randomizeItems, setRandomizeItems] = useState(false);
  const [useMatrixCompletion, setUseMatrixCompletion] = useState(true);
  const [clearCache, setClearCache] = useState(false);
  
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
      const parameters: TaskParameters = {
        use_iita: useIita,
        iita_max_diff: iitaMaxDiff,
        generations,
        patience,
        parallel,
        greedy,
        plot,
        randomize_items: randomizeItems,
        use_matrix_completion: useMatrixCompletion,
        clear_cache: clearCache,
        generate_png: generatePng,
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
    <div className="panel task-card">
      <div className="panel-head">
        <div>
          <p className="kicker">Step 2 · Configuration</p>
          <h3>Configure construction algorithm</h3>
          <p className="hint">Choose approach based on matrix size. NEAT for smaller sets, IITA for 100+ items.</p>
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

      <form className="task-form" onSubmit={handleSubmit}>
        <div className="section">
          <div className="section-title">
            <p className="kicker">Algorithm</p>
            <h4>Select approach</h4>
            <p className="hint">Settings adapt based on selection.</p>
          </div>
          <div className="choice-grid">
            <label className={`choice ${!useIita ? 'active' : ''}`}>
              <input type="radio" checked={!useIita} onChange={() => setUseIita(false)} />
              <div>
                <div className="choice-title">NEAT</div>
                <p className="hint">Evolutionary algorithm, faster for {'<'}100 items.</p>
              </div>
            </label>
            <label className={`choice ${useIita ? 'active' : ''}`}>
              <input type="radio" checked={useIita} onChange={() => setUseIita(true)} />
              <div>
                <div className="choice-title">IITA</div>
                <p className="hint">Inductive Item Tree Analysis for large matrices.</p>
              </div>
            </label>
          </div>
        </div>

        {useIita ? (
          <div className="section">
            <div className="section-title">
              <p className="kicker">IITA parameters</p>
              <h4>Relation precision</h4>
            </div>
            <div className="field-grid">
              <label className="field">
                <span>Max diff threshold</span>
                <input
                  type="number"
                  min="0.01"
                  max="0.2"
                  step="0.01"
                  value={iitaMaxDiff}
                  onChange={(e) => setIitaMaxDiff(parseFloat(e.target.value))}
                />
                <small>Default 0.08 · lower values = stricter prerequisites.</small>
              </label>
            </div>
          </div>
        ) : (
          <div className="section">
            <div className="section-title">
              <p className="kicker">NEAT parameters</p>
              <h4>Evolution dynamics</h4>
            </div>
            <div className="field-grid">
              <label className="field field-inline">
                <input
                  type="checkbox"
                  checked={greedy}
                  onChange={(e) => setGreedy(e.target.checked)}
                />
                <div>
                  <span>Greedy mode</span>
                  <small>Stop at first valid solution.</small>
                </div>
              </label>

              {!greedy && (
                <>
                  <label className="field">
                    <span>Generations (max)</span>
                    <input
                      type="number"
                      min="10"
                      max="500"
                      value={generations}
                      onChange={(e) => setGenerations(parseInt(e.target.value))}
                    />
                    <small>Number of evolution iterations.</small>
                  </label>
                  <label className="field">
                    <span>Patience</span>
                    <input
                      type="number"
                      min="5"
                      max="100"
                      value={patience}
                      onChange={(e) => setPatience(parseInt(e.target.value))}
                    />
                    <small>Early stop if no improvement.</small>
                  </label>
                </>
              )}

              <label className="field field-inline">
                <input
                  type="checkbox"
                  checked={parallel}
                  onChange={(e) => setParallel(e.target.checked)}
                />
                <div>
                  <span>Parallel processing</span>
                  <small>Better multi-core CPU utilization.</small>
                </div>
              </label>

              <label className="field field-inline">
                <input
                  type="checkbox"
                  checked={plot}
                  onChange={(e) => setPlot(e.target.checked)}
                />
                <div>
                  <span>Show graph during evolution</span>
                  <small>Visual feedback during execution.</small>
                </div>
              </label>
            </div>
          </div>
        )}

        <div className="section">
          <div className="section-title advanced-toggle" onClick={() => setShowAdvanced(!showAdvanced)}>
            <div>
              <p className="kicker">Advanced options</p>
              <h4>Input and output control</h4>
            </div>
            <span className="toggle">{showAdvanced ? 'Hide' : 'Show'}</span>
          </div>
          {showAdvanced && (
            <div className="field-grid">
              <label className="field field-inline">
                <input
                  type="checkbox"
                  checked={randomizeItems}
                  onChange={(e) => setRandomizeItems(e.target.checked)}
                />
                <div>
                  <span>Randomize items</span>
                  <small>Random column selection on each run.</small>
                </div>
              </label>

              <label className="field field-inline">
                <input
                  type="checkbox"
                  checked={useMatrixCompletion}
                  onChange={(e) => setUseMatrixCompletion(e.target.checked)}
                />
                <div>
                  <span>Matrix completion (ALS)</span>
                  <small>Fill missing values.</small>
                </div>
              </label>

              <label className="field field-inline">
                <input
                  type="checkbox"
                  checked={clearCache}
                  onChange={(e) => setClearCache(e.target.checked)}
                />
                <div>
                  <span>Clear cache before start</span>
                  <small>Clean environment guarantee.</small>
                </div>
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

        <div className="form-actions">
          <button type="submit" disabled={creating} className="primary-btn">
            <FiZap size={16} style={{ marginRight: '0.5rem' }} />
            {creating ? 'Launching...' : 'Launch analysis'}
          </button>
        </div>
      </form>

      {error && <div className="error-banner">{error}</div>}
    </div>
  );
}
