import { useState, useEffect } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline, Container, Box } from '@mui/material';
import { Home } from './components/Home';
import { UploadForm } from './components/UploadForm';
import { ProgressMonitor } from './components/ProgressMonitor';
import { ResultsDashboard } from './components/ResultsDashboard';
import { TaskHistory } from './components/TaskHistory';
import { academicTheme } from './theme';
import { storageService } from './utils/storageService';
import './App.css';

type AppStage = 'home' | 'upload' | 'progress' | 'results' | 'history';

function App() {
  const [stage, setStage] = useState<AppStage>('home');
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [isRestored, setIsRestored] = useState(false);

  // Restore state from storage on mount - but always start on home
  useEffect(() => {
    try {
      // Always start with home as landing page
      // Don't auto-restore to progress/results - that breaks UX
      const taskId = storageService.loadCurrentTaskId();
      if (taskId) {
        setCurrentTaskId(taskId);
        // User can view old task via history, but don't force navigation
      }
    } catch (error) {
      console.error('Error loading state:', error);
      storageService.clearAll();
    }
    setIsRestored(true);
  }, []);

  const handleNewAnalysis = () => {
    setStage('upload');
  };

  const handleViewHistory = () => {
    setStage('history');
  };

  const handleUploadStart = (taskId: string) => {
    setCurrentTaskId(taskId);
    storageService.saveCurrentTaskId(taskId);
    setStage('progress');
  };

  const handleAnalysisComplete = () => {
    setStage('results');
  };

  const handleViewTask = (taskId: string) => {
    setCurrentTaskId(taskId);
    storageService.saveCurrentTaskId(taskId);
    setStage('results');
  };

  const handleReset = () => {
    setCurrentTaskId(null);
    storageService.clearAll();
    setStage('home');
  };

  const handleBackToHome = () => {
    setStage('home');
  };

  const handleBackToHistory = () => {
    setStage('history');
  };

  if (!isRestored) {
    return null; // Show nothing while restoring
  }

  return (
    <ThemeProvider theme={academicTheme}>
      <CssBaseline />
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box className="app">
          {stage === 'home' && (
            <Home onNewAnalysis={handleNewAnalysis} onViewHistory={handleViewHistory} />
          )}

          {stage === 'upload' && (
            <UploadForm onUploadStart={handleUploadStart} onBack={handleReset} />
          )}

          {stage === 'progress' && currentTaskId && (
            <ProgressMonitor taskId={currentTaskId} onComplete={handleAnalysisComplete} />
          )}

          {stage === 'results' && currentTaskId && (
            <ResultsDashboard taskId={currentTaskId} onBack={handleBackToHome} onViewHistory={handleBackToHistory} />
          )}

          {stage === 'history' && (
            <TaskHistory onBack={handleReset} onViewTask={handleViewTask} />
          )}
        </Box>
      </Container>
    </ThemeProvider>
  );
}

export default App;
