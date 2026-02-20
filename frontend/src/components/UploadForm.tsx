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
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCsvFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (selectedFile.name.endsWith('.csv')) {
        setCsvFile(selectedFile);
        setError(null);
      } else {
        setError('Please select a CSV file');
        setCsvFile(null);
      }
    }
  };

  const handlePdfFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (selectedFile.name.endsWith('.pdf')) {
        setPdfFile(selectedFile);
        setError(null);
      } else {
        setError('Please select a PDF file');
        setPdfFile(null);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvFile || !pdfFile) {
      setError('Please select both CSV and PDF files');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await analysisAPI.runAnalysis(csvFile, pdfFile);
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
          Upload your CSV and PDF files to generate a knowledge space
        </Typography>

        <form onSubmit={handleSubmit} className="upload-form">
          <Box className="file-input-wrapper">
            <label
              htmlFor="csv-file-input"
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
              {csvFile ? csvFile.name : 'Choose CSV file...'}
            </label>
            <input
              id="csv-file-input"
              type="file"
              accept=".csv"
              onChange={handleCsvFileChange}
              disabled={loading}
              className="file-input"
            />
          </Box>

          <Box className="file-input-wrapper">
            <label
              htmlFor="pdf-file-input"
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
              {pdfFile ? pdfFile.name : 'Choose PDF file...'}
            </label>
            <input
              id="pdf-file-input"
              type="file"
              accept=".pdf"
              onChange={handlePdfFileChange}
              disabled={loading}
              className="file-input"
            />
          </Box>

          {error && <Box className="error-message">{error}</Box>}

          <Button
            type="submit"
            disabled={!csvFile || !pdfFile || loading}
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
            Expected Input Format
          </Typography>
          <Typography component="ul" sx={{ m: 0, pl: 2 }}>
            <Typography component="li">CSV: first row contains headers, rows contain student responses (0/1)</Typography>
            <Typography component="li">CSV: item code columns must match item codes present in the selected PDF</Typography>
            <Typography component="li">PDF: must contain item codes and full text of tasks</Typography>
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
