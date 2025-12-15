import { useState } from 'react';
import { UploadForm } from './components/UploadForm';
import { TaskForm } from './components/TaskForm';
import { TaskStatus } from './components/TaskStatus';
import type { Upload } from './types/api';
import './App.css';

function App() {
  const [currentUpload, setCurrentUpload] = useState<Upload | null>(null);
  const [currentTaskId, setCurrentTaskId] = useState<number | null>(null);

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

  return (
    <div className="app">
      <header>
        <h1>Learning Space Generator</h1>
        <p>Generate learning spaces using NEAT or IITA algorithms</p>
      </header>

      <main>
        {!currentUpload && (
          <UploadForm onUploadComplete={handleUploadComplete} />
        )}

        {currentUpload && !currentTaskId && (
          <>
            <TaskForm upload={currentUpload} onTaskCreated={handleTaskCreated} />
            <button onClick={handleReset}>Upload Different File</button>
          </>
        )}

        {currentTaskId && (
          <>
            <TaskStatus taskId={currentTaskId} />
            <button onClick={handleReset}>Start New Analysis</button>
          </>
        )}
      </main>
    </div>
  );
}

export default App;
