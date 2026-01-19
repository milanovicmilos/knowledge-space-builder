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
  // LSG Pipeline Options
  mode?: 'lsg_pipeline' | 'optimize' | 'manual';
  iita_threshold?: number;   // Default 0.05
  semantic_weight?: number;  // Default 0.3
  use_concept_level_iita?: boolean; // NEW: Default true - Run IITA on latent concepts instead of items
  
  // Legacy options (kept for compatibility)
  n_trials?: number;
  epochs?: number;
  latent_dim?: number;
  device?: string;
  pred_threshold?: number;
  implication_threshold?: number;
  min_known?: number;
  select_k?: number;
  min_support?: number;
  force_k?: boolean;
  generate_png?: boolean;
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
    trial?: number;
    max_trials?: number;
    trial_value?: number;
    trial_config?: {
      latent_dim?: number;
      epochs?: number;
      pred_threshold?: number;
      select_k?: number;
    };
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
