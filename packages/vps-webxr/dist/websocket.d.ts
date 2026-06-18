import { AgentPoseUpdate } from './types';
export declare function connectVpsWebSocket(url: string, sceneId: string, agentId: string, onUpdate: (agents: AgentPoseUpdate[]) => void, onError?: (error: Event) => void): WebSocket;
