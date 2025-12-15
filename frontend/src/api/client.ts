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

// Result endpoints
export const getResult = async (taskId: number) => {
  const { data } = await api.get(`/results/results/${taskId}`);
  return data;
};

export const downloadResult = async (taskId: number) => {
  const response = await api.get(`/results/results/${taskId}/download`, {
    responseType: 'blob',
  });
  return response.data;
};
