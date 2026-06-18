import { LocalizeResponse, MultiFrameLocalizeResponse, Scene, LocalizeOptions, MultiFrameLocalizeOptions } from './types';

function stripTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '');
}

function buildFormData(data: Record<string, any>): FormData {
  const fd = new FormData();
  for (const [key, value] of Object.entries(data)) {
    if (value !== undefined && value !== null) {
      fd.append(key, value);
    }
  }
  return fd;
}

export class VpsClient {
  private baseUrl: string;
  private apiKey?: string;

  constructor(baseUrl: string, apiKey?: string) {
    this.baseUrl = stripTrailingSlash(baseUrl);
    this.apiKey = apiKey;
  }

  private headers(): Record<string, string> {
    const h: Record<string, string> = {};
    if (this.apiKey) {
      h['X-API-Key'] = this.apiKey;
    }
    return h;
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const response = await fetch(url, {
      ...init,
      headers: {
        ...this.headers(),
        ...(init?.headers || {}),
      },
    });
    if (!response.ok) {
      let detail = `VPS API error: HTTP ${response.status}`;
      try {
        const payload = await response.json();
        detail = payload.detail || detail;
      } catch {
        // keep default
      }
      throw new Error(detail);
    }
    return response.json() as Promise<T>;
  }

  async getScene(sceneId: string): Promise<Scene> {
    return this.request<Scene>(`/scene/${sceneId}`);
  }

  async listScenes(): Promise<Scene[]> {
    return this.request<Scene[]>('/scene');
  }

  async localize(
    sceneId: string,
    image: Blob,
    options?: LocalizeOptions,
  ): Promise<LocalizeResponse> {
    const fd = buildFormData({
      scene_id: sceneId,
      query_image: image,
      agent_id: options?.agentId,
    });

    if (options?.hintPosition) {
      fd.append('hint_position', JSON.stringify(options.hintPosition));
    }
    if (options?.hintRadius !== undefined) {
      fd.append('hint_radius', String(options.hintRadius));
    }
    if (options?.hintFloorHeight) {
      fd.append('hint_floor_height', JSON.stringify(options.hintFloorHeight));
    }
    if (options?.geoHint) {
      fd.append('geo_hint', JSON.stringify(options.geoHint));
    }

    return this.request<LocalizeResponse>('/vps/localize', {
      method: 'POST',
      body: fd,
    });
  }

  async localizeMulti(
    sceneId: string,
    images: Blob[],
    options?: MultiFrameLocalizeOptions,
  ): Promise<MultiFrameLocalizeResponse> {
    const fd = buildFormData({
      scene_id: sceneId,
      agent_id: options?.agentId,
    });

    images.forEach((blob, i) => {
      fd.append(`image${i + 1}`, blob, `frame-${i}.jpg`);
    });

    if (options?.hintPosition) {
      fd.append('hint_position', JSON.stringify(options.hintPosition));
    }
    if (options?.hintRadius !== undefined) {
      fd.append('hint_radius', String(options.hintRadius));
    }

    return this.request<MultiFrameLocalizeResponse>('/vps/localize/multi', {
      method: 'POST',
      body: fd,
    });
  }
}
