import React, { useEffect, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Tab,
  Tabs,
  Card,
  CardContent,
  Grid,
  Button,
  CircularProgress,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  Divider,
  List,
  ListItemButton,
  ListItemText,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Info as InfoIcon,
  GetApp as GetAppIcon,
  Fullscreen as FullscreenIcon,
  Assessment as AssessmentIcon,
} from '@mui/icons-material';
import analysisAPI from '../api/analysis';
import { GraphModal } from './GraphModal';
import { storageService } from '../utils/storageService';
import './ResultsDashboard.css';

interface ResultsDashboardProps {
  taskId: string;
  onBack: () => void;
  onViewHistory: () => void;
}

interface Statistics {
  task_id: number;
  status: string;
  total_items: number;
  total_concepts: number;
  total_students: number;
  knowledge_space_states: number;
  prerequisites_found: number;
  semantic_clusters: number;
  root_concepts: number;
  difficulty_range?: { min: number; max: number };
  concepts_sorted_items?: number;
}

interface ResultFile {
  name: string;
  size: number;
  path: string;
}

interface LearningGoal {
  id: string;
  uri: string;
  label: string;
  item_count: number;
}

interface GoalPathItem {
  id: string;
  label: string;
  description: string | null;
  full_text?: string | null;
  difficulty?: number;
}

interface GoalPathStep {
  id: string;
  uri: string;
  label: string;
  item_count: number;
  items: GoalPathItem[];
  recommended_items?: GoalPathItem[];
  depth?: number;
  avg_difficulty?: number | null;
  prerequisites?: Array<{ id: string; label: string }>;
  prerequisite_evidence?: Array<{ id: string; weight: number }>;
}

interface GoalPathResponse {
  goal: { id: string; uri: string; label: string; is_known: boolean };
  known: string[];
  steps: GoalPathStep[];
  total_steps: number;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index } = props;

  return (
    <div hidden={value !== index} style={{ width: '100%' }}>
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

const truncateText = (value: string, maxLength: number) => {
  if (value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength).trim()}...`;
};

export const ResultsDashboard: React.FC<ResultsDashboardProps> = ({ taskId, onBack, onViewHistory }) => {
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [knowledgeSpace, setKnowledgeSpace] = useState<Record<string, string[]> | null>(null);
  const [files, setFiles] = useState<ResultFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [graphModalOpen, setGraphModalOpen] = useState(false);
  const [goals, setGoals] = useState<LearningGoal[]>([]);
  const [goalsLoading, setGoalsLoading] = useState(false);
  const [goalsError, setGoalsError] = useState<string | null>(null);
  const [selectedGoalId, setSelectedGoalId] = useState<string>('');
  const [goalPath, setGoalPath] = useState<GoalPathResponse | null>(null);
  const [goalPathLoading, setGoalPathLoading] = useState(false);
  const [goalPathError, setGoalPathError] = useState<string | null>(null);
  const [selectedStepId, setSelectedStepId] = useState<string>('');

  useEffect(() => {
    const loadResults = async () => {
      setLoading(true);
      setError(null);

      try {
        // Load statistics
        const statsData = await analysisAPI.getStatistics(taskId);
        // API returns statistics directly, not wrapped
        setStatistics(statsData);
        storageService.saveStatistics(statsData);

        // Load knowledge space
        try {
          const ksData = await analysisAPI.getKnowledgeSpace(taskId);
          // API returns {knowledge_space: {...}}
          if (ksData && ksData.knowledge_space) {
            setKnowledgeSpace(ksData.knowledge_space);
            storageService.saveKnowledgeSpace(ksData.knowledge_space);
          }
        } catch {
          // Knowledge space might not exist, try to load from storage
          const cached = storageService.loadKnowledgeSpace();
          if (cached) {
            setKnowledgeSpace(cached);
          }
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

  useEffect(() => {
    const loadGoals = async () => {
      setGoalsLoading(true);
      setGoalsError(null);

      try {
        const goalData = await analysisAPI.getGoals(taskId);
        setGoals(goalData.goals);
      } catch (err) {
        setGoalsError(err instanceof Error ? err.message : 'Failed to load goals');
      } finally {
        setGoalsLoading(false);
      }
    };

    loadGoals();
  }, [taskId]);

  useEffect(() => {
    const loadGoalPath = async () => {
      if (!selectedGoalId) {
        setGoalPath(null);
        return;
      }

      setGoalPathLoading(true);
      setGoalPathError(null);

      try {
        const pathData = await analysisAPI.getGoalPath(taskId, selectedGoalId);
        setGoalPath(pathData);
      } catch (err) {
        setGoalPathError(err instanceof Error ? err.message : 'Failed to load learning path');
      } finally {
        setGoalPathLoading(false);
      }
    };

    loadGoalPath();
  }, [taskId, selectedGoalId]);

  useEffect(() => {
    if (goalPath && goalPath.steps.length > 0) {
      setSelectedStepId(goalPath.steps[0].id);
    } else {
      setSelectedStepId('');
    }
  }, [goalPath]);

  const selectedStep = goalPath?.steps.find((step) => step.id === selectedStepId) || null;
  const totalPathItems = goalPath?.steps.reduce((sum, step) => sum + step.item_count, 0) || 0;
  const difficultyValues = goalPath?.steps
    .map((step) => step.avg_difficulty)
    .filter((value): value is number => value !== null && value !== undefined) || [];
  const avgPathDifficulty = difficultyValues.length > 0
    ? difficultyValues.reduce((sum, value) => sum + value, 0) / difficultyValues.length
    : null;
  const maxDepth = goalPath?.steps.reduce((value, step) => Math.max(value, step.depth ?? 0), 0) || 0;

  const handleDownloadFile = async (filePath: string, fileName: string) => {
    try {
      const data = await analysisAPI.downloadFile(filePath);
      const blob = new Blob([JSON.stringify(data, null, 2)]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      link.click();
    } catch (error) {
      console.error('Error downloading file:', error);
    }
  };

  if (loading) {
    return (
      <Box className="results-loading">
        <CircularProgress size={60} />
        <Typography variant="h6" sx={{ mt: 3 }}>Loading results...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box className="results-error-container">
        <Alert severity="error" sx={{ mb: 3, maxWidth: 600 }}>
          {error}
        </Alert>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', justifyContent: 'center' }}>
          <Button 
            startIcon={<ArrowBackIcon />} 
            onClick={onBack} 
            variant="contained"
            size="large"
          >
            Back to Home
          </Button>
          <Button 
            onClick={onViewHistory} 
            variant="outlined"
            size="large"
          >
            View History
          </Button>
        </Box>
      </Box>
    );
  }

  return (
    <Box className="results-dashboard-container">
      {/* Header Section - Similar to Home.tsx */}
      <Box className="results-header">
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mb: 2, gap: 2 }}>
          <AssessmentIcon sx={{ fontSize: 48, color: 'primary.main' }} />
          <Typography variant="h3" component="h1" sx={{ fontWeight: 600 }}>
            Analysis Results
          </Typography>
        </Box>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 1 }}>
          Task ID: {taskId} • {statistics?.status || 'Completed'}
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, mt: 2, flexWrap: 'wrap', justifyContent: 'center' }}>
          <Button 
            startIcon={<ArrowBackIcon />} 
            onClick={onBack}
            variant="contained"
            size="large"
          >
            Back to Home
          </Button>
          <Button 
            onClick={onViewHistory}
            variant="outlined"
            size="large"
          >
            View History
          </Button>
        </Box>
      </Box>

      {/* Tabs */}
      <Box className="results-tabs-container">
        <Paper elevation={2} sx={{ borderRadius: 2 }}>
          <Tabs
            value={tabValue}
            onChange={(_, newValue) => setTabValue(newValue)}
            aria-label="result tabs"
            centered
            sx={{
              '& .MuiTab-root': {
                fontSize: '1rem',
                fontWeight: 500,
                textTransform: 'none',
                minHeight: 64,
              },
            }}
          >
            <Tab label="Statistics Overview" />
            <Tab label="Knowledge Space Graph" disabled={!knowledgeSpace} />
            <Tab label="Learning Goal Path" />
            <Tab label="Download Files" />
          </Tabs>
        </Paper>
      </Box>

      {/* Tab Content */}
      <Box className="results-tab-content">

      {/* Statistics Tab */}
      <TabPanel value={tabValue} index={0}>
        {statistics && (
          <Box>
            {/* Main Data Statistics */}
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 3, ml: 1 }}>
              📊 Dataset Overview
            </Typography>
            <Grid container spacing={3} sx={{ mb: 4 }}>
              <Grid item xs={12} sm={6} md={4}>
                <Card elevation={3} className="stat-card">
                  <CardContent>
                    <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 600 }}>
                      Total Items
                    </Typography>
                    <Typography variant="h3" sx={{ my: 1, fontWeight: 700, color: 'primary.main' }}>
                      {statistics.total_items}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Test questions analyzed
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={4}>
                <Card elevation={3} className="stat-card">
                  <CardContent>
                    <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 600 }}>
                      Students
                    </Typography>
                    <Typography variant="h3" sx={{ my: 1, fontWeight: 700, color: 'success.main' }}>
                      {statistics.total_students}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Test participants analyzed
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={4}>
                <Card elevation={3} className="stat-card">
                  <CardContent>
                    <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 600 }}>
                      Avg. Items/Student
                    </Typography>
                    <Typography variant="h3" sx={{ my: 1, fontWeight: 700, color: 'info.main' }}>
                      {statistics.total_students > 0 
                        ? (statistics.total_items / statistics.total_students).toFixed(1)
                        : 0
                      }
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Data coverage per participant
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            {/* Knowledge Structure Statistics */}
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 3, ml: 1 }}>
              🧠 Knowledge Structure
            </Typography>
            <Grid container spacing={3} sx={{ mb: 4 }}>
              <Grid item xs={12} sm={6} md={4}>
                <Card elevation={3} className="stat-card">
                  <CardContent>
                    <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 600 }}>
                      Concepts
                    </Typography>
                    <Typography variant="h3" sx={{ my: 1, fontWeight: 700, color: 'secondary.main' }}>
                      {statistics.total_concepts}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Unique knowledge domains
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={4}>
                <Card elevation={3} className="stat-card">
                  <CardContent>
                    <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 600 }}>
                      Prerequisites
                    </Typography>
                    <Typography variant="h3" sx={{ my: 1, fontWeight: 700, color: 'warning.main' }}>
                      {statistics.prerequisites_found}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Concept dependencies found
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={4}>
                <Card elevation={3} className="stat-card">
                  <CardContent>
                    <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 600 }}>
                      Root Concepts
                    </Typography>
                    <Typography variant="h3" sx={{ my: 1, fontWeight: 700, color: 'error.main' }}>
                      {statistics.root_concepts}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Foundational concepts
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            {/* Learning Space Statistics */}
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 3, ml: 1 }}>
              📚 Learning Space Analysis
            </Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6} md={4}>
                <Card elevation={3} className="stat-card">
                  <CardContent>
                    <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 600 }}>
                      Knowledge States
                    </Typography>
                    <Typography variant="h3" sx={{ my: 1, fontWeight: 700, color: 'info.main' }}>
                      {statistics.knowledge_space_states}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Possible learning progressions
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={4}>
                <Card elevation={3} className="stat-card">
                  <CardContent>
                    <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 600 }}>
                      Semantic Groupings
                    </Typography>
                    <Typography variant="h3" sx={{ my: 1, fontWeight: 700 }}>
                      {statistics.semantic_clusters}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Related item clusters
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={4}>
                <Card elevation={3} className="stat-card">
                  <CardContent>
                    <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 600 }}>
                      Dependency Ratio
                    </Typography>
                    <Typography variant="h3" sx={{ my: 1, fontWeight: 700, color: 'primary.main' }}>
                      {statistics.total_concepts > 0
                        ? ((statistics.prerequisites_found / statistics.total_concepts) * 100).toFixed(0)
                        : 0
                      }%
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Concepts with prerequisites
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Box>
        )}
      </TabPanel>

      {/* Knowledge Space Tab */}
      <TabPanel value={tabValue} index={1}>
        {knowledgeSpace ? (
          <Box>
            <Card elevation={3} sx={{ p: 4, textAlign: 'center' }}>
              <Typography variant="h5" gutterBottom sx={{ fontWeight: 600 }}>
                Interactive Knowledge Space Visualization
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
                Explore the directed acyclic graph (DAG) representing prerequisite relationships 
                between {statistics?.total_concepts || 0} mathematical concepts.
              </Typography>
              <Button
                variant="contained"
                startIcon={<FullscreenIcon />}
                onClick={() => setGraphModalOpen(true)}
                size="large"
                sx={{ 
                  py: 1.5, 
                  px: 4,
                  fontSize: '1.1rem',
                }}
              >
                Open Knowledge Space Graph
              </Button>
              <Alert severity="info" icon={<InfoIcon />} sx={{ mt: 4, textAlign: 'left' }}>
                <strong>Knowledge Space contains {Object.keys(knowledgeSpace).length} possible learning states</strong>
                <br />
                Each state represents a unique combination of mastered concepts, 
                with edges showing valid learning progressions based on prerequisite relationships.
              </Alert>
            </Card>
          </Box>
        ) : (
          <Alert severity="warning">Knowledge space data not available</Alert>
        )}
      </TabPanel>

      {/* Learning Goal Path Tab */}
      <TabPanel value={tabValue} index={2}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Choose a Learning Goal
          </Typography>

          {goalsLoading && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <CircularProgress size={24} />
              <Typography>Loading goals...</Typography>
            </Box>
          )}

          {goalsError && (
            <Alert severity="error">{goalsError}</Alert>
          )}

          {!goalsLoading && !goalsError && (
            <FormControl sx={{ maxWidth: 480 }} fullWidth>
              <InputLabel id="goal-select-label">Learning Goal</InputLabel>
              <Select
                labelId="goal-select-label"
                value={selectedGoalId}
                label="Learning Goal"
                onChange={(event) => setSelectedGoalId(event.target.value)}
              >
                {goals.map((goal) => (
                  <MenuItem key={goal.id} value={goal.id}>
                    {goal.label} ({goal.item_count})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          {goalPathLoading && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <CircularProgress size={24} />
              <Typography>Building learning path...</Typography>
            </Box>
          )}

          {goalPathError && (
            <Alert severity="error">{goalPathError}</Alert>
          )}

          {!goalPathLoading && goalPath && (
            <Box className="goal-path-container">
              {goalPath.goal.is_known && (
                <Alert severity="info">
                  This goal is already marked as known.
                </Alert>
              )}

              {goalPath.steps.length === 0 && !goalPath.goal.is_known && (
                <Alert severity="warning">
                  No prerequisite path found for this goal.
                </Alert>
              )}

              {goalPath.steps.length > 0 && (
                <Box className="goal-summary-grid">
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={4}>
                      <Card elevation={2} className="goal-summary-card">
                        <CardContent>
                          <Typography variant="overline" color="text.secondary">
                            Selected Goal
                          </Typography>
                          <Typography variant="h6" sx={{ fontWeight: 600, mt: 1 }}>
                            {goalPath.goal.label}
                          </Typography>
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            Status: {goalPath.goal.is_known ? 'Known' : 'Not mastered'}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <Card elevation={2} className="goal-summary-card">
                        <CardContent>
                          <Typography variant="overline" color="text.secondary">
                            Path Complexity
                          </Typography>
                          <Typography variant="h6" sx={{ fontWeight: 600, mt: 1 }}>
                            {goalPath.total_steps} steps
                          </Typography>
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            Max depth: {maxDepth}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <Card elevation={2} className="goal-summary-card">
                        <CardContent>
                          <Typography variant="overline" color="text.secondary">
                            Learning Objects
                          </Typography>
                          <Typography variant="h6" sx={{ fontWeight: 600, mt: 1 }}>
                            {totalPathItems} objects
                          </Typography>
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            Avg. difficulty: {avgPathDifficulty !== null ? avgPathDifficulty.toFixed(2) : 'N/A'}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  </Grid>
                </Box>
              )}

              {goalPath.steps.length > 0 && (
                <Grid container spacing={3}>
                  <Grid item xs={12} md={4}>
                    <Card elevation={2} className="goal-outline-card">
                      <CardContent>
                        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                          Path Outline
                        </Typography>
                        <List dense className="goal-outline-list">
                          {goalPath.steps.map((step, index) => (
                            <ListItemButton
                              key={step.id}
                              selected={step.id === selectedStepId}
                              onClick={() => setSelectedStepId(step.id)}
                            >
                              <ListItemText
                                primary={goalPath.steps.length === 1 ? `Learning Goal: ${step.label}` : `Step ${index + 1}: ${step.label}`}
                                secondary={`${step.item_count} objects`}
                              />
                            </ListItemButton>
                          ))}
                        </List>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={8}>
                    <Card elevation={2} className="goal-detail-card">
                      <CardContent>
                        {selectedStep ? (
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                            <Box>
                              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                {selectedStep.label}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                Items: {selectedStep.item_count}
                                {selectedStep.avg_difficulty !== undefined && selectedStep.avg_difficulty !== null && (
                                  <> · Avg. difficulty: {selectedStep.avg_difficulty.toFixed(2)}</>
                                )}
                              </Typography>
                            </Box>

                            {selectedStep.prerequisites && selectedStep.prerequisites.length > 0 && (
                              <Box>
                                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                                  Prerequisites
                                </Typography>
                                <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
                                  {selectedStep.prerequisites.map((prereq) => (
                                    <Chip key={prereq.id} label={prereq.label} size="small" />
                                  ))}
                                </Stack>
                              </Box>
                            )}

                            <Divider />

                            <Box>
                              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                                Recommended learning objects
                              </Typography>
                              <Stack spacing={1}>
                                {selectedStep.items.map((item) => {
                                  const itemText = item.full_text || item.description || '';
                                  return (
                                    <Box key={item.id} sx={{ p: 1, borderRadius: 1, bgcolor: 'action.hover' }}>
                                      <Stack direction="row" spacing={1} alignItems="center" sx={{ flexWrap: 'wrap' }}>
                                        <Chip
                                          label={item.label}
                                          size="small"
                                          color={item.difficulty !== undefined ? 'primary' : 'default'}
                                        />
                                        {item.difficulty !== undefined && (
                                          <Typography variant="caption" color="text.secondary">
                                            diff: {item.difficulty.toFixed(2)}
                                          </Typography>
                                        )}
                                      </Stack>
                                      {itemText && (
                                        <Tooltip title={itemText} arrow>
                                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                                            {truncateText(itemText, 160)}
                                          </Typography>
                                        </Tooltip>
                                      )}
                                    </Box>
                                  );
                                })}
                              </Stack>
                            </Box>
                          </Box>
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            Select a step to see details.
                          </Typography>
                        )}
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              )}
            </Box>
          )}
        </Box>
      </TabPanel>

      {/* Files Tab */}
      <TabPanel value={tabValue} index={3}>
        {files.length > 0 ? (
          <Card elevation={3}>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow sx={{ backgroundColor: 'primary.main' }}>
                    <TableCell sx={{ color: 'white', fontWeight: 600, fontSize: '1rem' }}>
                      File Name
                    </TableCell>
                    <TableCell align="right" sx={{ color: 'white', fontWeight: 600, fontSize: '1rem' }}>
                      Size (KB)
                    </TableCell>
                    <TableCell align="center" sx={{ color: 'white', fontWeight: 600, fontSize: '1rem' }}>
                      Action
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {files.map((file, idx) => (
                    <TableRow 
                      key={idx}
                      sx={{ 
                        '&:hover': { backgroundColor: 'action.hover' },
                        transition: 'background-color 0.2s',
                      }}
                    >
                      <TableCell sx={{ fontSize: '0.95rem' }}>{file.name}</TableCell>
                      <TableCell align="right" sx={{ fontSize: '0.95rem' }}>
                        {(file.size / 1024).toFixed(2)}
                      </TableCell>
                      <TableCell align="center">
                        <Tooltip title={`Download ${file.name}`}>
                          <IconButton
                            onClick={() => handleDownloadFile(file.path, file.name)}
                            color="primary"
                            size="large"
                          >
                            <GetAppIcon />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Card>
        ) : (
          <Alert severity="info">No files available for download</Alert>
        )}
      </TabPanel>
      </Box>

      {/* Graph Modal */}
      {knowledgeSpace && (
        <GraphModal
          open={graphModalOpen}
          onClose={() => setGraphModalOpen(false)}
          knowledgeSpace={knowledgeSpace}
          title="Knowledge Space Graph"
        />
      )}
    </Box>
  );
};
