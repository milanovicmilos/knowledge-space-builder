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
  // Algorithm selection
  use_iita: boolean;
  
  // IITA options
  iita_max_diff: number;
  
  // NEAT options
  generations: number;
  patience: number;
  parallel: boolean;
  greedy: boolean;
  plot: boolean;
  
  // Data options
  randomize_items: boolean;
  use_matrix_completion: boolean;
  clear_cache: boolean;
  
  // Output options
  generate_png: boolean;
  png_filename?: string | null;
}

export interface Task {
  id: number;
  upload_id: number;
  status: string;
  celery_task_id: string | null;
  parameters: TaskParameters;
  progress_percent: number;
  current_generation: number | null;
  progress_details: {
    stage?: string;
    current_fitness?: number;
    best_fitness?: number;
    generation?: number;
    max_generation?: number;
    iteration?: number;
    max_iteration?: number;
    rmse?: number;
    current_item?: number;
    total_items?: number;
    eta_seconds?: number;
  } | null;
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
  result_metadata: Record<string, any> | null;
  created_at: string;
}
