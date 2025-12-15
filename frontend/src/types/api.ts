export interface Upload {
  id: number;
  filename: string;
  original_filename: string;
  storage_key: string;
  file_size_bytes: number;
  num_rows: number | null;
  num_columns: number | null;
  uploaded_at: string;
}

export interface TaskParameters {
  use_iita: boolean;
  iita_max_diff: number;
  generations: number;
  patience: number;
  parallel: boolean;
  use_matrix_completion: boolean;
}

export interface Task {
  id: number;
  upload_id: number;
  status: string;
  celery_task_id: string | null;
  parameters: TaskParameters;
  progress_percent: number;
  current_generation: number | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface Result {
  id: number;
  task_id: number;
  graph_storage_key: string;
  num_states: number | null;
  num_edges: number | null;
  num_relations: number | null;
  discrepancy: number | null;
  is_valid: boolean | null;
  algorithm: string;
  final_generation: number | null;
  execution_time_seconds: number | null;
  metadata: Record<string, any> | null;
  created_at: string;
}
