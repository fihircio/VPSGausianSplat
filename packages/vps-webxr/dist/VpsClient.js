"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.VpsClient = void 0;
function stripTrailingSlash(value) {
    return value.replace(/\/+$/, '');
}
function buildFormData(data) {
    const fd = new FormData();
    for (const [key, value] of Object.entries(data)) {
        if (value !== undefined && value !== null) {
            fd.append(key, value);
        }
    }
    return fd;
}
class VpsClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = stripTrailingSlash(baseUrl);
        this.apiKey = apiKey;
    }
    headers() {
        const h = {};
        if (this.apiKey) {
            h['X-API-Key'] = this.apiKey;
        }
        return h;
    }
    async request(path, init) {
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
            }
            catch {
                // keep default
            }
            throw new Error(detail);
        }
        return response.json();
    }
    async getScene(sceneId) {
        return this.request(`/scene/${sceneId}`);
    }
    async listScenes() {
        return this.request('/scene');
    }
    async localize(sceneId, image, options) {
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
        return this.request('/vps/localize', {
            method: 'POST',
            body: fd,
        });
    }
    async localizeMulti(sceneId, images, options) {
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
        return this.request('/vps/localize/multi', {
            method: 'POST',
            body: fd,
        });
    }
}
exports.VpsClient = VpsClient;
