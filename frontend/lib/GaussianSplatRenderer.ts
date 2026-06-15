import * as THREE from 'three';
import { Viewer } from '@mkkellogg/gaussian-splats-3d';

export class GaussianSplatRenderer {
  private viewer: Viewer | null = null;
  private threeScene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private isLoaded: boolean = false;

  constructor(threeScene: THREE.Scene, camera: THREE.PerspectiveCamera, renderer: THREE.WebGLRenderer) {
    this.threeScene = threeScene;
    this.camera = camera;
    this.renderer = renderer;
  }

  async load(url: string, onProgress?: (progress: number) => void): Promise<void> {
    if (this.viewer) {
      this.dispose();
    }

    // Initialize Viewer with existing scene/camera/renderer
    this.viewer = new Viewer({
      threeScene: this.threeScene,
      camera: this.camera,
      renderer: this.renderer,
      useBuiltInControls: false, // We use OrbitControls in the page
      gpuAcceleratedSort: true,
      halfPrecisionVideoTexture: true,
    });

    try {
      // url could be a .ply or .splat. The viewer automatically handles conversion for .ply natively!
      await this.viewer.addSplatScene(url, {
        showLoadingUI: false,
        onProgress: (p: number) => {
          if (onProgress) onProgress(p);
        }
      });
      this.viewer.start();
      this.isLoaded = true;
    } catch (error) {
      console.error('Failed to load Gaussian Splat:', error);
      throw error;
    }
  }

  update() {
    if (this.isLoaded && this.viewer) {
      this.viewer.update();
    }
  }

  dispose() {
    if (this.viewer) {
      this.viewer.dispose();
      this.viewer = null;
    }
    this.isLoaded = false;
  }
}
