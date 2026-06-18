export type VpsPose = {
  position: [number, number, number];
  rotation: [number, number, number, number];
  inliers: number;
  confidence: number;
};

export type VpsStatus = "idle" | "localizing" | "locked" | "weak" | "failed";

export type VpsLocalizationResult = {
  pose: VpsPose;
  status: VpsStatus;
  localizedAt: string;
};

const DEFAULT_API_BASE_URL = "";

export function getVpsApiBaseUrl(): string {
  return (process.env.REACT_APP_VPS_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

export function getVpsApiKey(): string {
  return process.env.REACT_APP_VPS_API_KEY || "";
}

function getVpsRequestHeaders(apiKey?: string): HeadersInit | undefined {
  const resolvedApiKey = apiKey || getVpsApiKey();
  return resolvedApiKey ? { "X-API-Key": resolvedApiKey } : undefined;
}

export function getDefaultSceneId(): string {
  return process.env.REACT_APP_SCENE_ID || "";
}

export function getDemoQueryImageUrl(sceneId: string): string {
  return (
    process.env.REACT_APP_DEMO_QUERY_IMAGE_URL ||
    `${getVpsApiBaseUrl()}/storage/frames/${sceneId}/frame_000002.jpg`
  );
}

export function poseToStatus(confidence: number, inliers: number): VpsStatus {
  if (confidence >= 0.5 && inliers >= 30) return "locked";
  if (confidence >= 0.3 && inliers >= 15) return "weak";
  return "failed";
}

const MAX_QUERY_DIMENSION = 1280;

export async function captureVideoFrame(
  video: HTMLVideoElement,
  maxDimension: number = MAX_QUERY_DIMENSION
): Promise<Blob> {
  if (!video.videoWidth || !video.videoHeight) {
    throw new Error("Camera frame is not ready yet.");
  }

  let w = video.videoWidth;
  let h = video.videoHeight;
  if (Math.max(w, h) > maxDimension) {
    const scale = maxDimension / Math.max(w, h);
    w = Math.round(w * scale);
    h = Math.round(h * scale);
  }

  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("Unable to create frame capture context.");
  }

  context.drawImage(video, 0, 0, w, h);

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error("Unable to encode camera frame."));
          return;
        }
        resolve(blob);
      },
      "image/jpeg",
      0.85
    );
  });
}

export async function localizeVideoFrame(params: {
  video: HTMLVideoElement;
  sceneId: string;
  agentId?: string;
  apiBaseUrl?: string;
  apiKey?: string;
}): Promise<VpsLocalizationResult> {
  const frameBlob = await captureVideoFrame(params.video);
  const formData = new FormData();
  formData.append("scene_id", params.sceneId);
  formData.append("query_image", frameBlob, "navigatus-frame.jpg");
  if (params.agentId) {
    formData.append("agent_id", params.agentId);
  }

  const apiBaseUrl = (params.apiBaseUrl || getVpsApiBaseUrl()).replace(/\/+$/, "");
  const response = await fetch(`${apiBaseUrl}/vps/localize`, {
    method: "POST",
    headers: getVpsRequestHeaders(params.apiKey),
    body: formData,
  });

  if (!response.ok) {
    let detail = `Localization failed with HTTP ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      // Keep default detail if response is not JSON.
    }
    throw new Error(detail);
  }

  const pose = (await response.json()) as VpsPose;
  return {
    pose,
    status: poseToStatus(pose.confidence, pose.inliers),
    localizedAt: new Date().toISOString(),
  };
}

export async function localizeImageBlob(params: {
  imageBlob: Blob;
  sceneId: string;
  agentId?: string;
  apiBaseUrl?: string;
  apiKey?: string;
}): Promise<VpsLocalizationResult> {
  const formData = new FormData();
  formData.append("scene_id", params.sceneId);
  formData.append("query_image", params.imageBlob, "navigatus-query.jpg");
  if (params.agentId) {
    formData.append("agent_id", params.agentId);
  }

  const apiBaseUrl = (params.apiBaseUrl || getVpsApiBaseUrl()).replace(/\/+$/, "");
  const response = await fetch(`${apiBaseUrl}/vps/localize`, {
    method: "POST",
    headers: getVpsRequestHeaders(params.apiKey),
    body: formData,
  });

  if (!response.ok) {
    let detail = `Localization failed with HTTP ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      // Keep default detail if response is not JSON.
    }
    throw new Error(detail);
  }

  const pose = (await response.json()) as VpsPose;
  return {
    pose,
    status: poseToStatus(pose.confidence, pose.inliers),
    localizedAt: new Date().toISOString(),
  };
}

export async function localizeDemoQueryImage(params: {
  sceneId: string;
  agentId?: string;
  apiBaseUrl?: string;
  apiKey?: string;
  imageUrl?: string;
}): Promise<VpsLocalizationResult> {
  const url = params.imageUrl || getDemoQueryImageUrl(params.sceneId);
  const imageResponse = await fetch(url);
  if (!imageResponse.ok) {
    throw new Error(`Demo query frame unavailable: HTTP ${imageResponse.status}`);
  }
  const imageBlob = await imageResponse.blob();
  return localizeImageBlob({
    imageBlob,
    sceneId: params.sceneId,
    agentId: params.agentId,
    apiBaseUrl: params.apiBaseUrl,
    apiKey: params.apiKey,
  });
}
