import * as THREE from 'three';
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader.js';
import { TileManifest, TileNode } from '../types';
import { api } from './api';

export class TileManager {
  private sceneId: string;
  private manifest: TileManifest | null = null;
  private nodesMap: Map<string, TileNode> = new Map();
  private loadedTiles: Map<string, THREE.Points> = new Map();
  private loadingTiles: Set<string> = new Set();
  private loader: PLYLoader;
  private threeScene: THREE.Scene;
  
  // Configuration
  private maxCachedTiles = 12;
  private lodDistanceThreshold = 10; // Simple distance-based LOD control

  constructor(sceneId: string, threeScene: THREE.Scene) {
    this.sceneId = sceneId;
    this.threeScene = threeScene;
    this.loader = new PLYLoader();
  }

  async init() {
    try {
      this.manifest = await api.getTileManifest(this.sceneId);
      if (this.manifest) {
        this.manifest.nodes.forEach(node => {
          this.nodesMap.set(node.node_id, node);
        });
      }
    } catch (error) {
      console.error('Failed to load tile manifest:', error);
      throw error;
    }
  }

  update(camera: THREE.PerspectiveCamera) {
    if (!this.manifest) return;

    const frustum = new THREE.Frustum();
    const projScreenMatrix = new THREE.Matrix4();
    projScreenMatrix.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    frustum.setFromProjectionMatrix(projScreenMatrix);

    const visibleNodeIds: string[] = [];
    this.traverseOctree(this.getRootNode()!, frustum, camera, visibleNodeIds);

    // 1. Determine which tiles to load
    visibleNodeIds.forEach(nodeId => {
      if (!this.loadedTiles.has(nodeId) && !this.loadingTiles.has(nodeId)) {
        this.loadTile(nodeId);
      }
    });

    // 2. Determine which tiles to hide/remove (Frustum Culling + LRU-ish cache limit)
    const activeNodes = new Set(visibleNodeIds);
    this.loadedTiles.forEach((mesh, nodeId) => {
      if (!activeNodes.has(nodeId)) {
        mesh.visible = false;
        // If we exceed cache limit, actually remove it from scene
        if (this.loadedTiles.size > this.maxCachedTiles) {
          this.threeScene.remove(mesh);
          this.loadedTiles.delete(nodeId);
        }
      } else {
        mesh.visible = true;
      }
    });
  }

  private getRootNode(): TileNode | undefined {
    return this.nodesMap.get('root');
  }

  private traverseOctree(node: TileNode, frustum: THREE.Frustum, camera: THREE.Camera, visibleIds: string[]) {
    // Check if node's BBox intersects frustum
    const bbox = new THREE.Box3(
      new THREE.Vector3(...node.bbox_min),
      new THREE.Vector3(...node.bbox_max)
    );

    if (!frustum.intersectsBox(bbox)) return;

    // Simple LOD logic: if distance is far, use parent if it were available
    // But our current tiling is leaf-only for data delivery.
    // If it's a leaf, add to visible. If not, traverse children.
    if (node.is_leaf) {
      visibleIds.push(node.node_id);
    } else {
      node.children.forEach(childId => {
        const child = this.nodesMap.get(childId);
        if (child) this.traverseOctree(child, frustum, camera, visibleIds);
      });
    }
  }

  private async loadTile(nodeId: string) {
    this.loadingTiles.add(nodeId);
    const url = `http://localhost:8000/storage/splats/${this.sceneId}/tiles/tile_${nodeId}.ply`;

    return new Promise<void>((resolve, reject) => {
      this.loader.load(url, (geometry) => {
        const material = new THREE.PointsMaterial({
          size: 0.04,
          vertexColors: true,
          transparent: true,
          opacity: 0.9
        });
        const points = new THREE.Points(geometry, material);
        points.userData = { nodeId };
        
        this.threeScene.add(points);
        this.loadedTiles.set(nodeId, points);
        this.loadingTiles.delete(nodeId);
        resolve();
      }, undefined, (err) => {
        console.error(`Error loading tile ${nodeId}:`, err);
        this.loadingTiles.delete(nodeId);
        reject(err);
      });
    });
  }

  dispose() {
    this.loadedTiles.forEach(mesh => {
      this.threeScene.remove(mesh);
      mesh.geometry.dispose();
      (mesh.material as THREE.Material).dispose();
    });
    this.loadedTiles.clear();
    this.loadingTiles.clear();
  }
}
