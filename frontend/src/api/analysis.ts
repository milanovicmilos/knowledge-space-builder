import axios, { type AxiosInstance } from 'axios';

interface AnalysisStatus {
  task_id: string;
  status: 'initializing' | 'running' | 'completed' | 'failed';
  progress: number;
  message: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

interface AnalysisResults {
  task_id: string;
  status: string;
  completed_at: string;
  files: Record<string, any>;
}

interface AnalysisStatistics {
  task_id: number;
  status: string;
  total_items: number;
  total_concepts: number;
  total_students: number;
  knowledge_space_states: number;
  prerequisites_found: number;
  semantic_clusters: number;
  root_concepts: number;
}

class AnalysisAPI {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: '/api/v1/analysis',
      timeout: 30000,
    });
  }

  async runAnalysis(file: File): Promise<{ task_id: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.api.post('/run', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  async getStatus(taskId: string): Promise<AnalysisStatus> {
    const response = await this.api.get(`/${taskId}/status`);
    return response.data;
  }

  async getResults(taskId: string): Promise<AnalysisResults> {
    const response = await this.api.get(`/${taskId}/results`);
    return response.data;
  }

  async getStatistics(taskId: string): Promise<AnalysisStatistics> {
    const response = await this.api.get(`/${taskId}/statistics`);
    return response.data;
  }

  async getVisualization(taskId: string): Promise<{ graph_file: string; graph_exists: boolean }> {
    const response = await this.api.get(`/${taskId}/visualization`);
    return response.data;
  }

  async listFiles(taskId: string): Promise<{ files: Array<{ name: string; size: number; path: string }> }> {
    const response = await this.api.get(`/${taskId}/files`);
    return response.data;
  }

  async getKnowledgeSpace(taskId: string): Promise<{ knowledge_space: Record<string, string[]> }> {
    const response = await this.api.get(`/${taskId}/knowledge-space`);
    return response.data;
  }

  async downloadFile(filePath: string): Promise<any> {
    const response = await this.api.get(`/download`, {
      params: { path: filePath },
    });
    return response.data;
  }

  async getAllTasks(): Promise<{ tasks: any[]; total_count: number }> {
    const response = await this.api.get('/tasks');
    return response.data;
  }

  async deleteTask(taskId: number): Promise<{ success: boolean; message: string }> {
    const response = await this.api.delete(`/${taskId}`);
    return response.data;
  }
}

export default new AnalysisAPI();
