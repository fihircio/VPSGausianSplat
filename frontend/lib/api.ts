import axios from 'axios';
import { Scene, SceneProcessResponse, LocalizeResponse, EvaluationReport, EvaluationResponse, SceneFramesResponse, Anchor, AnchorCreate } from '../types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
});

export const api = {
  // Scene Upload
  async listScenes(): Promise<Scene[]> {
    const { data } = await client.get<Scene[]>('/scene');
    return data;
  },

  async uploadScene(file: File, name?: string): Promise<Scene> {
    const formData = new FormData();
    formData.append('file', file);
    if (name) formData.append('name', name);
    const { data } = await client.post<Scene>('/scene/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  // Trigger Processing
  async processScene(sceneId: string): Promise<SceneProcessResponse> {
    const { data } = await client.post<SceneProcessResponse>(`/scene/${sceneId}/process`);
    return data;
  },

  // Get Scene Status
  async getScene(sceneId: string): Promise<Scene> {
    const { data } = await client.get<Scene>(`/scene/${sceneId}`);
    return data;
  },

  // Localize Image
  async localize(sceneId: string, image: File): Promise<LocalizeResponse> {
    const formData = new FormData();
    formData.append('scene_id', sceneId);
    formData.append('query_image', image);
    const { data } = await client.post<LocalizeResponse>('/vps/localize', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  // Get Evaluation Summary
  async getEvaluation(sceneId: string): Promise<EvaluationResponse> {
    const { data } = await client.get<EvaluationResponse>(`/vps/evaluation/${sceneId}`);
    return data;
  },

  // Get Scene Frames (Poses)
  async getSceneFrames(sceneId: string): Promise<SceneFramesResponse> {
    const { data } = await client.get<SceneFramesResponse>(`/scene/${sceneId}/frames`);
    return data;
  },

  async purgeSceneStorage(sceneId: string): Promise<any> {
    const { data } = await client.delete(`/scene/${sceneId}/cleanup`);
    return data;
  },

  // Tile Management
  async getTileManifest(sceneId: string): Promise<any> {
    const { data } = await client.get(`/scene/${sceneId}/tiles/manifest`);
    return data;
  },

  // Anchors
  async listAnchors(sceneId: string): Promise<Anchor[]> {
    const { data } = await client.get<Anchor[]>(`/scene/${sceneId}/anchors`);
    return data;
  },

  async createAnchor(sceneId: string, anchor: AnchorCreate): Promise<Anchor> {
    const { data } = await client.post<Anchor>(`/scene/${sceneId}/anchors`, anchor);
    return data;
  },

  async deleteAnchor(sceneId: string, anchorId: string): Promise<void> {
    await client.delete(`/scene/${sceneId}/anchors/${anchorId}`);
  },

  // Mock Dashboard Data (Fall-back)
  getMockReport(): EvaluationReport {
    return {
      scene_id: "demo-scene-id",
      num_frames: 154,
      sampled_frame_indices: [1, 10, 20, 30, 40],
      best_config: {
        config: { orb_nfeatures: 2000, pixel_distance_threshold: 5, ratio_test_threshold: 0.7 },
        score: 92.4,
        summary: {
          success_rate: 0.94,
          avg_inliers: 68.2,
          avg_confidence: 0.81,
          avg_translation_error: 0.12,
          avg_rotation_error: 2.4
        }
      },
      worst_config: {
        config: { orb_nfeatures: 500, pixel_distance_threshold: 3, ratio_test_threshold: 0.8 },
        score: 45.1,
        summary: {
          success_rate: 0.42,
          avg_inliers: 12.5,
          avg_confidence: 0.23,
          avg_translation_error: 1.45,
          avg_rotation_error: 15.2
        }
      },
      recommended_settings: { orb_nfeatures: 2000, pixel_distance_threshold: 5, ratio_test_threshold: 0.7 },
      config_results: []
    };
  }
};
