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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Info as InfoIcon,
  GetApp as GetAppIcon,
  Fullscreen as FullscreenIcon,
} from '@mui/icons-material';
import analysisAPI from '../api/analysis';
import { GraphModal } from './GraphModal';
import { storageService } from '../utils/storageService';

interface ResultsDashboardProps {
  taskId: string;
  onReset: () => void;
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

export const ResultsDashboard: React.FC<ResultsDashboardProps> = ({ taskId, onReset }) => {
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [knowledgeSpace, setKnowledgeSpace] = useState<Record<string, string[]> | null>(null);
  const [files, setFiles] = useState<ResultFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [graphModalOpen, setGraphModalOpen] = useState(false);

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
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={onReset} variant="outlined">
          Back to Upload
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Analysis Results
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Task ID: {taskId}
          </Typography>
        </Box>
        <Button startIcon={<ArrowBackIcon />} onClick={onReset} variant="outlined">
          Back
        </Button>
      </Box>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={tabValue}
          onChange={(_, newValue) => setTabValue(newValue)}
          aria-label="result tabs"
        >
          <Tab label="Statistics" />
          <Tab label="Knowledge Space" disabled={!knowledgeSpace} />
          <Tab label="Files" />
        </Tabs>
      </Paper>

      {/* Statistics Tab */}
      <TabPanel value={tabValue} index={0}>
        {statistics && (
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={4}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Total Items
                  </Typography>
                  <Typography variant="h4">{statistics.total_items}</Typography>
                  <Typography variant="body2" color="textSecondary">
                    Test questions analyzed
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={4}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Concepts
                  </Typography>
                  <Typography variant="h4">{statistics.total_concepts}</Typography>
                  <Typography variant="body2" color="textSecondary">
                    Unique knowledge concepts
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={4}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Students
                  </Typography>
                  <Typography variant="h4">{statistics.total_students}</Typography>
                  <Typography variant="body2" color="textSecondary">
                    Test participants analyzed
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={4}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Knowledge States
                  </Typography>
                  <Typography variant="h4">{statistics.knowledge_space_states}</Typography>
                  <Typography variant="body2" color="textSecondary">
                    Possible learning states
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={4}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Prerequisites
                  </Typography>
                  <Typography variant="h4">{statistics.prerequisites_found}</Typography>
                  <Typography variant="body2" color="textSecondary">
                    Concept dependencies
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={4}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Root Concepts
                  </Typography>
                  <Typography variant="h4">{statistics.root_concepts}</Typography>
                  <Typography variant="body2" color="textSecondary">
                    No prerequisites required
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={4}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Semantic Clusters
                  </Typography>
                  <Typography variant="h4">{statistics.semantic_clusters}</Typography>
                  <Typography variant="body2" color="textSecondary">
                    Item groupings
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={4}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Sorted Items
                  </Typography>
                  <Typography variant="h4">{statistics.concepts_sorted_items ?? 'N/A'}</Typography>
                  <Typography variant="body2" color="textSecondary">
                    By difficulty
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}
      </TabPanel>

      {/* Knowledge Space Tab */}
      <TabPanel value={tabValue} index={1}>
        {knowledgeSpace ? (
          <Box>
            <Box sx={{ mb: 3 }}>
              <Button
                variant="contained"
                startIcon={<FullscreenIcon />}
                onClick={() => setGraphModalOpen(true)}
                size="large"
              >
                Open Knowledge Space Graph
              </Button>
            </Box>
            <Alert severity="info" icon={<InfoIcon />}>
              Knowledge Space contains {Object.keys(knowledgeSpace).length} possible learning states
              in a directed acyclic graph (DAG) representing prerequisite relationships between
              mathematical concepts.
            </Alert>
          </Box>
        ) : (
          <Alert severity="warning">Knowledge space data not available</Alert>
        )}
      </TabPanel>

      {/* Files Tab */}
      <TabPanel value={tabValue} index={2}>
        {files.length > 0 ? (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                  <TableCell>File Name</TableCell>
                  <TableCell align="right">Size (KB)</TableCell>
                  <TableCell align="center">Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {files.map((file, idx) => (
                  <TableRow key={idx}>
                    <TableCell>{file.name}</TableCell>
                    <TableCell align="right">{(file.size / 1024).toFixed(2)}</TableCell>
                    <TableCell align="center">
                      <Button
                        startIcon={<GetAppIcon />}
                        onClick={() => handleDownloadFile(file.path, file.name)}
                        size="small"
                        variant="outlined"
                      >
                        Download
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Alert severity="info">No files available</Alert>
        )}
      </TabPanel>

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
