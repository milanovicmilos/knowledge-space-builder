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
  // MIRT-VAE Training options
  epochs: number;
  latent_dim: number;
  device: string;
  
  // Prerequisite graph options
  pred_threshold: number;
  implication_threshold: number;
  min_known: number;
  
  // Lattice construction options
  select_k: number;
  min_support: number;
  force_k: boolean;
  
  // Output options
  generate_png: boolean;
}

export interface Task {
  id: number;
  upload_id: number;
  status: string;
  celery_task_id: string | null;
  parameters: TaskParameters;
  progress_percent: number;
  current_epoch: number | null;  // Changed from current_generation
  progress_details: {
    stage?: string;
    current_loss?: number;  // Changed from current_fitness
    epoch?: number;  // Changed from generation
    max_epochs?: number;  // Changed from max_generation
    num_states?: number;
    total_unique?: number;
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
