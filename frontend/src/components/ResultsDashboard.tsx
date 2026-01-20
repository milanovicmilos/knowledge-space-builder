import React, { useEffect, useState } from 'react';
import './ResultsDashboard.css';
import analysisAPI from '../api/analysis';

interface ResultsDashboardProps {
  taskId: string;
  onReset: () => void;
}

interface Statistics {
  total_items: number;
  total_concepts: number;
  total_students: number;
  knowledge_space_states: number;
  prerequisites_found: number;
  semantic_clusters: number;
  root_concepts: number;
  difficulty_range: { min: number; max: number };
  concepts_sorted_items: number;
}

interface ResultFile {
  name: string;
  size: number;
  path: string;
}

export const ResultsDashboard: React.FC<ResultsDashboardProps> = ({ taskId, onReset }) => {
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [graphUrl, setGraphUrl] = useState<string | null>(null);
  const [files, setFiles] = useState<ResultFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'stats' | 'graph' | 'files'>('stats');

  useEffect(() => {
    const loadResults = async () => {
      setLoading(true);
      setError(null);

      try {
        // Load statistics
        const statsData = await analysisAPI.getStatistics(taskId);
        setStatistics(statsData.statistics);

        // Load visualization
        try {
          const vizData = await analysisAPI.getVisualization(taskId);
          if (vizData.graph_exists) {
            setGraphUrl(vizData.graph_file);
          }
        } catch {
          // Graph might not exist, that's ok
        }

        // Load files
        const filesData = await analysisAPI.listFiles(taskId);
        setFiles(filesData.files);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load results');
      } finally {
        setLoading(false);
      }
    };

    loadResults();
  }, [taskId]);

  if (loading) {
    return <div className="results-loading">Loading results...</div>;
  }

  if (error) {
    return (
      <div className="results-error">
        <p>Error: {error}</p>
        <button onClick={onReset}>← Back</button>
      </div>
    );
  }

  return (
    <div className="results-dashboard">
      <div className="dashboard-header">
        <h1>📊 Analysis Results</h1>
        <p>Task ID: {taskId}</p>
      </div>

      <div className="dashboard-tabs">
        <button
          className={`tab-btn ${activeTab === 'stats' ? 'active' : ''}`}
          onClick={() => setActiveTab('stats')}
        >
          📈 Statistics
        </button>
        <button
          className={`tab-btn ${activeTab === 'graph' ? 'active' : ''}`}
          onClick={() => setActiveTab('graph')}
        >
          📊 Visualization
        </button>
        <button
          className={`tab-btn ${activeTab === 'files' ? 'active' : ''}`}
          onClick={() => setActiveTab('files')}
        >
          📁 Files
        </button>
      </div>

      {/* STATISTICS TAB */}
      {activeTab === 'stats' && statistics && (
        <div className="tab-content">
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon">📝</div>
              <div className="stat-label">Total Items</div>
              <div className="stat-value">{statistics.total_items}</div>
              <div className="stat-description">Test questions analyzed</div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">🎯</div>
              <div className="stat-label">Concepts</div>
              <div className="stat-value">{statistics.total_concepts}</div>
              <div className="stat-description">Unique knowledge concepts</div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">👥</div>
              <div className="stat-label">Students</div>
              <div className="stat-value">{statistics.total_students}</div>
              <div className="stat-description">Test participants analyzed</div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">🌐</div>
              <div className="stat-label">Knowledge States</div>
              <div className="stat-value">{statistics.knowledge_space_states}</div>
              <div className="stat-description">Possible learning states</div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">🔗</div>
              <div className="stat-label">Prerequisites</div>
              <div className="stat-value">{statistics.prerequisites_found}</div>
              <div className="stat-description">Concept dependencies</div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">🏷️</div>
              <div className="stat-label">Semantic Clusters</div>
              <div className="stat-value">{statistics.semantic_clusters}</div>
              <div className="stat-description">Semantically similar groups</div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">🌳</div>
              <div className="stat-label">Root Concepts</div>
              <div className="stat-value">{statistics.root_concepts}</div>
              <div className="stat-description">Starting points (no prerequisites)</div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">📊</div>
              <div className="stat-label">Item Difficulty</div>
              <div className="stat-value">
                {statistics.difficulty_range?.min ? 
                  `${(statistics.difficulty_range.min * 100).toFixed(1)}% - ${(statistics.difficulty_range.max * 100).toFixed(1)}%` :
                  'N/A'
                }
              </div>
              <div className="stat-description">Easiest to hardest items</div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">⭐</div>
              <div className="stat-label">Sorted Items</div>
              <div className="stat-value">{statistics.concepts_sorted_items}</div>
              <div className="stat-description">Concepts with difficulty ranking</div>
            </div>
          </div>

          <div className="stats-explanation">
            <h3>📖 Understanding the Results</h3>
            <ul>
              <li>
                <strong>Total Items:</strong> Number of test questions that were analyzed (121)
              </li>
              <li>
                <strong>Concepts:</strong> Unique mathematical concepts identified by LLM (25)
              </li>
              <li>
                <strong>Students:</strong> Number of students whose responses were analyzed (692)
              </li>
              <li>
                <strong>Knowledge States:</strong> All possible valid combinations of concepts (355)
              </li>
              <li>
                <strong>Prerequisites:</strong> Statistically valid concept dependencies found (30)
              </li>
              <li>
                <strong>Semantic Clusters:</strong> Groups of semantically similar items (24)
              </li>
              <li>
                <strong>Root Concepts:</strong> Concepts with no prerequisites, starting points (8)
              </li>
              <li>
                <strong>Difficulty Range:</strong> Min/max of student success rates on items
              </li>
            </ul>
          </div>
        </div>
      )}

      {/* VISUALIZATION TAB */}
      {activeTab === 'graph' && (
        <div className="tab-content">
          {graphUrl ? (
            <div className="graph-container">
              <h3>Knowledge Structure Graph</h3>
              <img src={graphUrl} alt="Knowledge Structure Graph" className="graph-image" />
              <p className="graph-description">
                This graph shows all {statistics?.knowledge_space_states} valid knowledge states and how they connect
                based on prerequisite relationships.
              </p>
            </div>
          ) : (
            <div className="no-graph">
              <p>📊 Visualization not available yet</p>
              <p>The graph may still be generating. Please refresh in a moment.</p>
            </div>
          )}
        </div>
      )}

      {/* FILES TAB */}
      {activeTab === 'files' && (
        <div className="tab-content">
          <div className="files-container">
            <h3>Generated Files ({files.length})</h3>
            <div className="files-list">
              {files.map((file) => (
                <div key={file.name} className="file-item">
                  <div className="file-icon">
                    {file.name.endsWith('.json') ? '📄' : file.name.endsWith('.csv') ? '📊' : file.name.endsWith('.png') ? '🖼️' : file.name.endsWith('.ttl') ? '🌐' : '📁'}
                  </div>
                  <div className="file-info">
                    <div className="file-name">{file.name}</div>
                    <div className="file-size">{(file.size / 1024).toFixed(1)} KB</div>
                  </div>
                  <div className="file-action">
                    <a href={`/api/v1/analysis/${taskId}/file/${file.name}`} target="_blank" rel="noopener noreferrer">
                      Open →
                    </a>
                  </div>
                </div>
              ))}
            </div>

            <div className="file-descriptions">
              <h4>File Descriptions</h4>
              <dl>
                <dt>knowledge_space.json</dt>
                <dd>All valid knowledge states and transitions between them</dd>

                <dt>implications.json</dt>
                <dd>Prerequisite relationships between concepts</dd>

                <dt>llm_item_classifications.json</dt>
                <dd>Mapping of items to concepts (LLM classification)</dd>

                <dt>semantic_clusters.json</dt>
                <dd>Groups of semantically similar items</dd>

                <dt>aggregated_concepts.csv</dt>
                <dd>Student mastery scores for each concept</dd>

                <dt>item_difficulties.json</dt>
                <dd>Difficulty of each item (% of students correct)</dd>

                <dt>concepts_sorted_by_difficulty.json</dt>
                <dd>Items within each concept sorted by difficulty</dd>

                <dt>sotis_ontology.ttl</dt>
                <dd>RDF/TTL format for semantic web integration (SOTIS)</dd>

                <dt>knowledge_structure_graph.png</dt>
                <dd>Visual representation of the knowledge structure</dd>
              </dl>
            </div>
          </div>
        </div>
      )}

      <div className="dashboard-footer">
        <button onClick={onReset} className="reset-btn">
          ← Analyze Another Dataset
        </button>
      </div>
    </div>
  );
};
