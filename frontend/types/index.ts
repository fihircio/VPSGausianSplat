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
  progress_percent: number;
  current_task_label: string | null;
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

export interface EvaluationSummary {
  scene_id: string;
  num_frames: number;
  success_rate: number;
  avg_inliers: number;
  avg_confidence: number;
  avg_translation_error: number;
  avg_rotation_error: number;
}

export interface EvaluationResponse {
  summary: EvaluationSummary;
  config: any;
}

export interface Frame {
  id: number;
  frame_index: number;
  image_path: string;
  intrinsics_json: any;
  pose_json: any;
}

export interface SceneFramesResponse {
  scene_id: string;
  frames: Frame[];
}

export interface Anchor {
  id: string;
  scene_id: string;
  label: string;
  position: [number, number, number];
  rotation: [number, number, number, number]; // [qx, qy, qz, qw]
  glb_url: string | null;
  created_at: string;
}

export interface AnchorCreate {
  label: string;
  position: [number, number, number];
  rotation?: [number, number, number, number];
  glb_url?: string | null;
}

export interface TileNode {
  node_id: string;
  depth: number;
  bbox_min: [number, number, number];
  bbox_max: [number, number, number];
  point_count: number;
  is_leaf: boolean;
  children: string[];
}

export interface TileManifest {
  scene_id: string;
  generated_at: string;
  total_points: number;
  max_points_per_tile: number;
  bbox_min: [number, number, number];
  bbox_max: [number, number, number];
  nodes: TileNode[];
}
