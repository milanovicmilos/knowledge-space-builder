import React, { useState } from 'react';
import './UploadForm.css';
import analysisAPI from '../api/analysis';
import { Assessment as AssessmentIcon, Description as DescriptionIcon } from '@mui/icons-material';

interface UploadFormProps {
  onUploadStart: (taskId: string) => void;
}

export const UploadForm: React.FC<UploadFormProps> = ({ onUploadStart }) => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (selectedFile.name.endsWith('.csv')) {
        setFile(selectedFile);
        setError(null);
      } else {
        setError('Please select a CSV file');
        setFile(null);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a file');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await analysisAPI.runAnalysis(file);
      onUploadStart(result.task_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload file');
      setLoading(false);
    }
  };

  return (
    <div className="upload-form-container">
      <div className="upload-form">
        <h2>
          <AssessmentIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Knowledge Space Generator
        </h2>
        <p>Upload your CSV file to generate a knowledge space</p>

        <form onSubmit={handleSubmit}>
          <div className="file-input-wrapper">
            <label htmlFor="file-input" className="file-input-label">
              {file ? file.name : 'Choose CSV file...'}
            </label>
            <input
              id="file-input"
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              disabled={loading}
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" disabled={!file || loading} className="submit-btn">
            {loading ? 'Uploading...' : 'Start Analysis'}
          </button>
        </form>

        <div className="info-box">
          <h3>
            <DescriptionIcon sx={{ mr: 1, verticalAlign: 'middle', fontSize: '1.2rem' }} />
            Expected CSV Format
          </h3>
          <ul>
            <li>First row: Column headers (student ID, item IDs)</li>
            <li>Rows: Student responses (0 = incorrect, 1 = correct)</li>
            <li>Columns: Student ID + Item responses</li>
            <li>Example: student_id,s1m11a091,s1m11a101,s1m12a191...</li>
          </ul>
        </div>
      </div>
    </div>
  );
};
