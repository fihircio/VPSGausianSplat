export interface Scene {
  id: string;
  name: string;
  status: 'UPLOADED' | 'QUEUED' | 'PROCESSING' | 'READY' | 'FAILED';
  input_type: 'video' | 'image';
  input_path: string;
  frames_dir: string;
  sparse_dir: string | null;
  splat_path: string | null;
  faiss_index_path: string | null;
  error_message: string | null;
  frame_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface SceneProcessResponse {
  scene_id: string;
  task_id: string;
  status: string;
}

export interface LocalizeResponse {
  position: [number, number, number];
  rotation: [number, number, number, number];
  inliers: number;
  confidence: number;
}

export interface EvaluationReport {
  scene_id: string;
  num_frames: number;
  sampled_frame_indices: number[];
  best_config: any;
  worst_config: any;
  recommended_settings: any;
  config_results: any[];
}
