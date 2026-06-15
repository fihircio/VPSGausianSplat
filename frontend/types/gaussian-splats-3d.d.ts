declare module '@mkkellogg/gaussian-splats-3d' {
  import * as THREE from 'three';
  export class Viewer {
    constructor(options?: Record<string, unknown>);
    addSplatScene(url: string, options?: Record<string, unknown>): Promise<void>;
    start(): void;
    stop(): void;
    update(): void;
    dispose(): void;
  }
}
