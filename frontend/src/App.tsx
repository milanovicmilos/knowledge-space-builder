import { useState } from 'react';
import { UploadForm } from './components/UploadForm';
import { ProgressMonitor } from './components/ProgressMonitor';
import { ResultsDashboard } from './components/ResultsDashboard';
import './App.css';

type AppStage = 'upload' | 'progress' | 'results';

function App() {
  const [stage, setStage] = useState<AppStage>('upload');
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);

  const handleUploadStart = (taskId: string) => {
    setCurrentTaskId(taskId);
    setStage('progress');
  };

  const handleAnalysisComplete = () => {
    setStage('results');
  };

  const handleReset = () => {
    setCurrentTaskId(null);
    setStage('upload');
  };

  return (
    <div className="app">
      {stage === 'upload' && <UploadForm onUploadStart={handleUploadStart} />}

      {stage === 'progress' && currentTaskId && (
        <ProgressMonitor taskId={currentTaskId} onComplete={handleAnalysisComplete} />
      )}

      {stage === 'results' && currentTaskId && (
        <ResultsDashboard taskId={currentTaskId} onReset={handleReset} />
      )}
    </div>
  );
}

export default App;
