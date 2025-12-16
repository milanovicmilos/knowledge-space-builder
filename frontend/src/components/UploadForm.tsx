import { useState } from 'react';
import { FiUpload } from 'react-icons/fi';
import { uploadCSV } from '../api/client';
import type { Upload } from '../types/api';
import './UploadForm.css';

interface UploadFormProps {
  onUploadComplete?: (upload: Upload) => void;
}

export function UploadForm({ onUploadComplete }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const MAX_SIZE_BYTES = 100 * 1024 * 1024; // 100MB

  const selectedMeta = file
    ? `${(file.size / 1024).toFixed(1)} KB · ${file.type || 'text/csv'}`
    : null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      // Client-side size guard for quick feedback
      if (file.size > MAX_SIZE_BYTES) {
        setError('File exceeds 100MB limit. Please upload a smaller file.');
        setUploading(false);
        return;
      }
      const upload = await uploadCSV(file);
      onUploadComplete?.(upload);
      setFile(null);
    } catch (err: any) {
      if (err?.response?.status === 413) {
        setError('File exceeds 100MB limit. Please upload a smaller file.');
      } else {
        setError(err?.response?.data?.detail || 'Upload failed');
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="panel upload-card">
      <div className="panel-head">
        <div>
          <p className="kicker">Step 1 · Data upload</p>
          <h3>Import CSV dataset</h3>
          <p className="hint">Assessment data (rows = subjects, columns = items, values 0/1).</p>
        </div>
        <div className="pill soft">Server-side validation</div>
      </div>

      <form className="upload-form" onSubmit={handleSubmit}>
        <label className="dropzone">
          <input
            type="file"
            accept=".csv"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            disabled={uploading}
          />
          {file ? (
            <div className="file-meta">
              <span className="file-name">{file.name}</span>
              <span className="file-size">{selectedMeta}</span>
            </div>
          ) : (
            <div>
              <p className="drop-title">Drag and drop or select CSV</p>
              <p className="drop-sub">Max 100MB · UTF-8 · delimiter auto-detected</p>
            </div>
          )}
        </label>

        <div className="upload-actions">
          <button type="submit" className="primary-btn" disabled={!file || uploading}>
            <FiUpload size={16} style={{ marginRight: '0.5rem' }} />
            {uploading ? 'Uploading...' : 'Upload and validate'}
          </button>
          <p className="hint">Data is not persisted; used only for the current analysis session.</p>
        </div>
      </form>

      {error && <div className="error-banner">{error}</div>}
    </div>
  );
}
