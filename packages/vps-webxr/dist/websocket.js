"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.connectVpsWebSocket = connectVpsWebSocket;
function connectVpsWebSocket(url, sceneId, agentId, onUpdate, onError) {
    const ws = new WebSocket(url);
    ws.onopen = () => {
        ws.send(JSON.stringify({
            type: 'subscribe',
            scene_id: sceneId,
            agent_id: agentId,
        }));
    };
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'agent_updates' && Array.isArray(data.agents)) {
                onUpdate(data.agents);
            }
        }
        catch {
            // Ignore malformed messages
        }
    };
    ws.onerror = (error) => {
        onError?.(error);
    };
    return ws;
}
