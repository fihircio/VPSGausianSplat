export interface LocalizeResponse {
    position: [number, number, number];
    rotation: [number, number, number, number];
    inliers: number;
    confidence: number;
    hint_used: string | null;
}
export interface MultiFrameLocalizeResponse extends LocalizeResponse {
    frames_used: number;
    frame_confidences: number[];
}
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
export interface AgentPoseUpdate {
    agent_id: string;
    position: [number, number, number];
    rotation: [number, number, number, number];
    confidence: number;
    inliers: number;
    timestamp: string;
}
export interface LocalizeOptions {
    hintPosition?: [number, number, number];
    hintRadius?: number;
    hintFloorHeight?: [number, number];
    geoHint?: {
        lat: number;
        lng: number;
    };
    agentId?: string;
}
export interface MultiFrameLocalizeOptions {
    hintPosition?: [number, number, number];
    hintRadius?: number;
    agentId?: string;
}
