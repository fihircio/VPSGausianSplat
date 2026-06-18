import { AgentPoseUpdate } from './types';

export function connectVpsWebSocket(
  url: string,
  sceneId: string,
  agentId: string,
  onUpdate: (agents: AgentPoseUpdate[]) => void,
  onError?: (error: Event) => void,
): WebSocket {
  const ws = new WebSocket(url);

  ws.onopen = () => {
    ws.send(JSON.stringify({
      type: 'subscribe',
      scene_id: sceneId,
      agent_id: agentId,
    }));
  };

  ws.onmessage = (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'agent_updates' && Array.isArray(data.agents)) {
        onUpdate(data.agents as AgentPoseUpdate[]);
      }
    } catch {
      // Ignore malformed messages
    }
  };

  ws.onerror = (error: Event) => {
    onError?.(error);
  };

  return ws;
}
