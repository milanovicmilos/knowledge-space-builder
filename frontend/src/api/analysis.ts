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
  task_id: string;
  status: string;
  statistics: {
    total_items: number;
    total_concepts: number;
    total_students: number;
    knowledge_space_states: number;
    prerequisites_found: number;
    semantic_clusters: number;
    root_concepts: number;
    difficulty_range: { min: number; max: number };
    concepts_sorted_items: number;
  };
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
}

export default new AnalysisAPI();
