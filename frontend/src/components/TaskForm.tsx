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
  // Item clustering options
  const [cluster, setCluster] = useState(true);
  const [rowCoverageThresh, setRowCoverageThresh] = useState(0.1);
  const [minPairs, setMinPairs] = useState(500);
  const [maxItemClusters, setMaxItemClusters] = useState<number | null>(null);
  
  // NEAT options
  const [generations, setGenerations] = useState(50);
  const [patience, setPatience] = useState(20);
  const [parallel, setParallel] = useState(true);
  const [greedy, setGreedy] = useState(false);
  const [plot, setPlot] = useState(false);
  
  // Missing value handling
  const [missingMatchReward, setMissingMatchReward] = useState(0.5);
  const [missingMismatchPenalty, setMissingMismatchPenalty] = useState(1.0);
  
  // Data options
  const [randomizeItems, setRandomizeItems] = useState(false);
  
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
        cluster,
        row_coverage_thresh: rowCoverageThresh,
        min_pairs: minPairs,
        max_item_clusters: maxItemClusters,
        generations,
        patience,
        parallel,
        greedy,
        plot,
        missing_match_reward: missingMatchReward,
        missing_mismatch_penalty: missingMismatchPenalty,
        randomize_items: randomizeItems,
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
          <h3>Configure NEAT Algorithm</h3>
          <p className="hint">Evolutionary algorithm with automatic item clustering for large datasets.</p>
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
            <p className="kicker">Item Clustering</p>
            <h4>Automatic data partitioning</h4>
            <p className="hint">Divides large datasets into optimal subsets for processing.</p>
          </div>
          <div className="field-grid">
            <label className="field field-inline">
              <input
                type="checkbox"
                checked={cluster}
                onChange={(e) => setCluster(e.target.checked)}
              />
              <div>
                <span>Enable clustering</span>
                <small>Recommended for 50+ items.</small>
              </div>
            </label>

            {cluster && (
              <>
                <label className="field">
                  <span>Row coverage threshold</span>
                  <input
                    type="number"
                    min="0.01"
                    max="1.0"
                    step="0.01"
                    value={rowCoverageThresh}
                    onChange={(e) => setRowCoverageThresh(parseFloat(e.target.value))}
                  />
                  <small>Students with ≥this% answered items (sparse data: 0.05-0.15, dense: 0.8).</small>
                </label>
                <label className="field">
                  <span>Minimum pairs per cluster</span>
                  <input
                    type="number"
                    min="100"
                    max="5000"
                    step="50"
                    value={minPairs}
                    onChange={(e) => setMinPairs(parseInt(e.target.value))}
                  />
                  <small>Minimum item-pair combinations required.</small>
                </label>
                <label className="field">
                  <span>Max item clusters (optional)</span>
                  <input
                    type="number"
                    min="2"
                    max="20"
                    value={maxItemClusters ?? ''}
                    placeholder="Auto"
                    onChange={(e) => setMaxItemClusters(e.target.value ? parseInt(e.target.value) : null)}
                  />
                  <small>Leave empty for automatic selection.</small>
                </label>
              </>
            )}
          </div>
        </div>

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

        <div className="section">
          <div className="section-title advanced-toggle" onClick={() => setShowAdvanced(!showAdvanced)}>
            <div>
              <p className="kicker">Advanced options</p>
              <h4>Missing values & output control</h4>
            </div>
            <span className="toggle">{showAdvanced ? 'Hide' : 'Show'}</span>
          </div>
          {showAdvanced && (
            <div className="field-grid">
              <label className="field">
                <span>Missing match reward</span>
                <input
                  type="number"
                  min="0"
                  max="2"
                  step="0.1"
                  value={missingMatchReward}
                  onChange={(e) => setMissingMatchReward(parseFloat(e.target.value))}
                />
                <small>Reward when both values are missing (0.5).</small>
              </label>

              <label className="field">
                <span>Missing mismatch penalty</span>
                <input
                  type="number"
                  min="0"
                  max="5"
                  step="0.1"
                  value={missingMismatchPenalty}
                  onChange={(e) => setMissingMismatchPenalty(parseFloat(e.target.value))}
                />
                <small>Penalty when one value is missing (1.0).</small>
              </label>

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
