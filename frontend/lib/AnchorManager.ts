import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { api } from './api';
import { Anchor, AnchorCreate } from '../types';

export class AnchorManager {
  private sceneId: string;
  private threeScene: THREE.Scene;
  private anchors: Map<string, { data: Anchor, mesh: THREE.Group }> = new Map();
  private loader: GLTFLoader;

  constructor(sceneId: string, threeScene: THREE.Scene) {
    this.sceneId = sceneId;
    this.threeScene = threeScene;
    this.loader = new GLTFLoader();
  }

  async loadAnchors() {
    try {
      const anchorsData = await api.listAnchors(this.sceneId);
      for (const anchor of anchorsData) {
        await this.spawnGLB(anchor);
      }
    } catch (err) {
      console.error('Failed to load anchors:', err);
    }
  }

  async createAnchor(pos: THREE.Vector3, label: string, glbUrl?: string) {
    const defaultGlb = 'https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/main/2.0/Box/glTF-Binary/Box.glb';
    
    // We send Y-up coordinates assuming they match the point cloud orientation
    const createPayload: AnchorCreate = {
      label,
      position: [pos.x, pos.y, pos.z],
      rotation: [0, 0, 0, 1], // Identity fallback
      glb_url: glbUrl || defaultGlb,
    };

    try {
      const newAnchor = await api.createAnchor(this.sceneId, createPayload);
      await this.spawnGLB(newAnchor);
      return newAnchor;
    } catch (err) {
      console.error('Failed to create anchor:', err);
      throw err;
    }
  }

  async deleteAnchor(anchorId: string) {
    try {
      await api.deleteAnchor(this.sceneId, anchorId);
      const entry = this.anchors.get(anchorId);
      if (entry) {
        this.threeScene.remove(entry.mesh);
        // Clean up geometries
        entry.mesh.traverse((obj) => {
          if ((obj as THREE.Mesh).isMesh) {
            const mesh = obj as THREE.Mesh;
            mesh.geometry.dispose();
            if (Array.isArray(mesh.material)) {
              mesh.material.forEach(m => m.dispose());
            } else {
              mesh.material.dispose();
            }
          }
        });
        this.anchors.delete(anchorId);
      }
    } catch (err) {
      console.error('Failed to delete anchor:', err);
      throw err;
    }
  }

  private spawnGLB(anchor: Anchor): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!anchor.glb_url) {
        resolve(); // Cannot spawn without URL
        return;
      }

      this.loader.load(anchor.glb_url, (gltf) => {
        const model = gltf.scene;
        model.position.set(anchor.position[0], anchor.position[1], anchor.position[2]);
        model.quaternion.set(anchor.rotation[0], anchor.rotation[1], anchor.rotation[2], anchor.rotation[3]);
        
        // Scale down the sample Box to fit in AR scenarios nicely
        model.scale.set(0.2, 0.2, 0.2); 
        
        // Add custom data for raycasting identification
        model.userData = { isAnchor: true, anchorId: anchor.id, label: anchor.label };

        this.threeScene.add(model);
        this.anchors.set(anchor.id, { data: anchor, mesh: model });
        resolve();
      }, undefined, (err) => {
        console.error(`Error spawning GLB for anchor ${anchor.id}:`, err);
        // We still resolve so other anchors can load, but log the error
        resolve();
      });
    });
  }

  getAnchorsList(): Anchor[] {
    return Array.from(this.anchors.values()).map(a => a.data);
  }

  dispose() {
    this.anchors.forEach(entry => {
      this.threeScene.remove(entry.mesh);
      entry.mesh.traverse((obj) => {
        if ((obj as THREE.Mesh).isMesh) {
          const mesh = obj as THREE.Mesh;
          mesh.geometry.dispose();
          if (Array.isArray(mesh.material)) {
            mesh.material.forEach(m => m.dispose());
          } else {
            mesh.material.dispose();
          }
        }
      });
    });
    this.anchors.clear();
  }
}
