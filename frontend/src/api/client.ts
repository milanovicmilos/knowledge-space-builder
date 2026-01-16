import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Upload endpoints
export const uploadCSV = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/uploads/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export const getUploads = async () => {
  const { data } = await api.get('/uploads');
  return data;
};

// Task endpoints
export const createTask = async (uploadId: number, parameters: any) => {
  const { data } = await api.post('/tasks/tasks', {
    upload_id: uploadId,
    parameters,
  });
  return data;
};

export const getTask = async (taskId: number) => {
  const { data } = await api.get(`/tasks/tasks/${taskId}`);
  return data;
};

export const getTasks = async () => {
  const { data } = await api.get('/tasks/tasks');
  return data;
};

export const deleteTask = async (taskId: number) => {
  await api.delete(`/tasks/tasks/${taskId}`);
};

// Result endpoints
export const getResult = async (taskId: number) => {
  const { data } = await api.get(`/results/${taskId}`);
  return data;
};

export const downloadResult = async (taskId: number) => {
  const response = await api.get(`/results/${taskId}/download`, {
    responseType: 'blob',
  });
  return response.data;
};

// Results listing
export const listResults = async (params?: {
  limit?: number;
  offset?: number;
  algorithm?: 'neat' | 'iita' | string;
  upload_id?: number;
  date_from?: string; // ISO
  date_to?: string;   // ISO
}) => {
  const { data } = await api.get('/results', { params });
  return data as { total: number; items: Array<{
    result_id: number; task_id: number; status: string; algorithm: string;
    created_at: string; completed_at?: string | null; upload_id: number;
    upload_filename: string; num_states?: number | null; num_edges?: number | null;
    has_png: boolean;
  }>};
};

export const deleteResult = async (taskId: number) => {
  await api.delete(`/results/${taskId}`);
};
