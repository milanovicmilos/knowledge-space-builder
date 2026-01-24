import React, { useState } from 'react';
import './UploadForm.css';
import {
  Box,
  Button,
  Typography,
  Paper,
  IconButton,
} from '@mui/material';
import {
  Assessment as AssessmentIcon,
  Description as DescriptionIcon,
  ArrowBack as ArrowBackIcon,
  CloudUpload as CloudUploadIcon,
} from '@mui/icons-material';
import analysisAPI from '../api/analysis';

interface UploadFormProps {
  onUploadStart: (taskId: string) => void;
  onBack: () => void;
}

export const UploadForm: React.FC<UploadFormProps> = ({ onUploadStart, onBack }) => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

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
    <Box className="upload-container">
      <Paper className="upload-content" elevation={2}>
        <Box className="upload-header">
          <Box className="upload-title">
            <IconButton onClick={onBack} size="small" sx={{ mr: 1 }}>
              <ArrowBackIcon />
            </IconButton>
            <AssessmentIcon sx={{ color: 'primary.main' }} />
            <Typography variant="h5" sx={{ fontWeight: 600 }}>
              New Analysis
            </Typography>
          </Box>
        </Box>

        <Typography variant="body1" sx={{ mb: 3, color: 'text.secondary' }}>
          Upload your CSV file to generate a knowledge space
        </Typography>

        <form onSubmit={handleSubmit} className="upload-form">
          <Box className="file-input-wrapper">
            <label
              htmlFor="file-input"
              className="file-input-label"
            >
              <CloudUploadIcon
                sx={{
                  fontSize: 40,
                  display: 'block',
                  mb: 1,
                  color: 'primary.main',
                }}
              />
              {file ? file.name : 'Choose CSV file...'}
            </label>
            <input
              ref={fileInputRef}
              id="file-input"
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              disabled={loading}
              className="file-input"
            />
          </Box>

          {error && <Box className="error-message">{error}</Box>}

          <Button
            type="submit"
            disabled={!file || loading}
            variant="contained"
            fullWidth
            sx={{ mt: 2 }}
          >
            {loading ? 'Uploading...' : 'Start Analysis'}
          </Button>
        </form>

        <Box className="info-box">
          <Typography component="div" className="info-box h3">
            <DescriptionIcon sx={{ fontSize: 20 }} />
            Expected CSV Format
          </Typography>
          <Typography component="ul" sx={{ m: 0, pl: 2 }}>
            <Typography component="li">First row: Column headers (student ID, item IDs)</Typography>
            <Typography component="li">Rows: Student responses (0 = incorrect, 1 = correct)</Typography>
            <Typography component="li">Columns: Student ID + Item responses</Typography>
            <Typography component="li">Example: student_id,s1m11a091,s1m11a101,s1m12a191...</Typography>
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
};
