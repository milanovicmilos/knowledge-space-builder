import { useState, useEffect } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline, Container, Box } from '@mui/material';
import { UploadForm } from './components/UploadForm';
import { ProgressMonitor } from './components/ProgressMonitor';
import { ResultsDashboard } from './components/ResultsDashboard';
import { academicTheme } from './theme';
import { storageService } from './utils/storageService';
import './App.css';

type AppStage = 'upload' | 'progress' | 'results';

function App() {
  const [stage, setStage] = useState<AppStage>('upload');
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [isRestored, setIsRestored] = useState(false);

  // Restore state from storage on mount
  useEffect(() => {
    try {
      const taskId = storageService.loadCurrentTaskId();
      if (taskId) {
        setCurrentTaskId(taskId);
        // Determine stage based on task data
        const stats = storageService.loadStatistics();
        if (stats) {
          setStage('results');
        } else {
          setStage('progress');
        }
      }
    } catch (error) {
      console.error('Error loading statistics:', error);
      // If there's an error loading from storage, start fresh
      storageService.clearAll();
    }
    setIsRestored(true);
  }, []);

  const handleUploadStart = (taskId: string) => {
    setCurrentTaskId(taskId);
    storageService.saveCurrentTaskId(taskId);
    setStage('progress');
  };

  const handleAnalysisComplete = () => {
    setStage('results');
  };

  const handleReset = () => {
    setCurrentTaskId(null);
    storageService.clearAll();
    setStage('upload');
  };

  if (!isRestored) {
    return null; // Show nothing while restoring
  }

  return (
    <ThemeProvider theme={academicTheme}>
      <CssBaseline />
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box className="app">
          {stage === 'upload' && <UploadForm onUploadStart={handleUploadStart} />}

          {stage === 'progress' && currentTaskId && (
            <ProgressMonitor taskId={currentTaskId} onComplete={handleAnalysisComplete} />
          )}

          {stage === 'results' && currentTaskId && (
            <ResultsDashboard taskId={currentTaskId} onReset={handleReset} />
          )}
        </Box>
      </Container>
    </ThemeProvider>
  );
}

export default App;
