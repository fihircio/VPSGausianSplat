"use client";

import { useState, useEffect, useRef, use } from 'react';
import { useRouter } from 'next/navigation';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader.js';
import { Activity, ArrowLeft, Maximize, RotateCcw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';
import { Scene } from '@/types';

export default function SceneViewerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const containerRef = useRef<HTMLDivElement>(null);
  const [sceneData, setSceneData] = useState<Scene | null>(null);
  const [frames, setFrames] = useState<any[]>([]);
  const [selectedFrame, setSelectedFrame] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(0);
  const router = useRouter();

  useEffect(() => {
    api.getScene(id).then(setSceneData).catch(console.error);
    api.getSceneFrames(id).then(res => setFrames(res.frames)).catch(console.error);
  }, [id]);

  useEffect(() => {
    if (!containerRef.current || !sceneData) return;

    // --- Scene Setup ---
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x050505);

    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    containerRef.current.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;

    // --- Helpers ---
    const grid = new THREE.GridHelper(50, 50, 0x1a1a1a, 0x0f0f0f);
    grid.position.y = -2;
    scene.add(grid);
    scene.add(new THREE.AmbientLight(0xffffff, 0.8));

    // --- Interaction ---
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    const frustumObjects: THREE.Object3D[] = [];

    // --- Load Data ---
    const loader = new PLYLoader();
    const url = `http://localhost:8000/storage/splats/${id}/sparse_points_fallback.ply`;

    loader.load(url, (geometry) => {
      const material = new THREE.PointsMaterial({ 
        size: 0.04, // Larger points for visibility
        vertexColors: true,
        opacity: 0.9,
        transparent: true
      });
      const points = new THREE.Points(geometry, material);
      
      geometry.computeBoundingBox();
      const center = new THREE.Vector3();
      geometry.boundingBox?.getCenter(center);
      points.position.sub(center);
      scene.add(points);
      
      controls.target.set(0, 0, 0);
      camera.position.set(5, 5, 5);
      setLoading(false);
    }, (xhr) => {
      if (xhr.lengthComputable) setProgress(Math.round((xhr.loaded / xhr.total) * 100));
    });

    // --- Camera Poses ---
    if (frames?.length) {
      const frustumGeom = new THREE.ConeGeometry(0.12, 0.25, 4);
      frustumGeom.rotateX(Math.PI / 2);
      const frustumMat = new THREE.MeshBasicMaterial({ color: 0x4f46e5, wireframe: true });

      frames.forEach((f) => {
        if (!f.pose_json) return;
        const pos = f.pose_json.position_wc;
        const rot = f.pose_json.rotation_wc;

        const mesh = new THREE.Mesh(frustumGeom, frustumMat.clone());
        mesh.position.set(pos[0], pos[1], pos[2]);
        const m4 = new THREE.Matrix4();
        m4.set(rot[0][0], rot[0][1], rot[0][2], 0, rot[1][0], rot[1][1], rot[1][2], 0, rot[2][0], rot[2][1], rot[2][2], 0, 0, 0, 0, 1);
        mesh.quaternion.setFromRotationMatrix(m4);
        mesh.userData = { frame: f };
        scene.add(mesh);
        frustumObjects.push(mesh);
      });
    }

    // --- Events ---
    const handleClick = (event: MouseEvent) => {
      mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
      mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(frustumObjects);
      if (intersects.length > 0) {
        const frame = (intersects[0].object as any).userData.frame;
        setSelectedFrame(frame);
        // Highlight logic
        frustumObjects.forEach(obj => ((obj as THREE.Mesh).material as THREE.MeshBasicMaterial).color.set(0x4f46e5));
        ((intersects[0].object as THREE.Mesh).material as THREE.MeshBasicMaterial).color.set(0xec4899);
      }
    };
    window.addEventListener('click', handleClick);

    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', handleResize);

    const animate = () => {
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      window.removeEventListener('click', handleClick);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      if (containerRef.current) containerRef.current.removeChild(renderer.domElement);
    };
  }, [sceneData, id, frames]);

  return (
    <div className="relative h-screen w-full bg-[#050505] overflow-hidden font-geist">
      {/* Header HUD */}
      <div className="absolute top-0 left-0 right-0 p-8 z-10 flex items-start justify-between pointer-events-none">
        <button onClick={() => router.back()} className="p-4 bg-white/5 backdrop-blur-3xl border border-white/10 rounded-3xl text-white hover:bg-white/10 transition-all pointer-events-auto shadow-2xl">
          <ArrowLeft className="h-6 w-6" />
        </button>
        <div className="text-right">
          <div className="px-4 py-1.5 bg-indigo-500/10 border border-indigo-500/20 rounded-full inline-block backdrop-blur-xl">
             <span className="text-indigo-400 text-[10px] font-black uppercase tracking-[0.2em]">Clinical Visualizer 2.0</span>
          </div>
          <h1 className="mt-4 text-4xl font-black text-white uppercase tracking-tighter">{sceneData?.name || "Initializing..."}</h1>
        </div>
      </div>

      <div ref={containerRef} className="h-full w-full" />

      {/* Frame Preview HUD (Bottom Middle) */}
      <AnimatePresence>
        {selectedFrame && (
          <motion.div 
            initial={{ y: 200, x: '-50%', opacity: 0 }}
            animate={{ y: 0, x: '-50%', opacity: 1 }}
            exit={{ y: 200, x: '-50%', opacity: 0 }}
            className="absolute bottom-10 left-1/2 -translate-x-1/2 w-[400px] z-30"
          >
            <div className="glass-card overflow-hidden bg-black/60 border-indigo-500/30">
              <div className="relative aspect-video bg-gray-900">
                <img 
                  src={`http://localhost:8000${selectedFrame.image_path}`} 
                  alt="Frame View"
                  className="w-full h-full object-cover"
                />
                <div className="absolute top-4 left-4 px-3 py-1 bg-black/60 backdrop-blur-md rounded-lg border border-white/10">
                  <span className="text-[10px] font-black text-white/80 uppercase">Frame {selectedFrame.frame_index}</span>
                </div>
              </div>
              <div className="p-5 flex items-center justify-between">
                <div>
                  <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Capture Angle</p>
                  <p className="text-white font-bold font-mono text-sm mt-1">
                    {selectedFrame.pose_json.position_wc.map((v: number) => v.toFixed(2)).join(', ')}
                  </p>
                </div>
                <button 
                  onClick={() => setSelectedFrame(null)}
                  className="p-2 hover:bg-white/10 rounded-xl transition-colors text-white/40"
                >
                  <RotateCcw className="h-4 w-4" />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading Overlay */}
      {loading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#050505] z-50">
          <Activity className="h-16 w-16 text-indigo-500 animate-spin mb-8" />
          <div className="w-64 h-1.5 bg-white/5 rounded-full overflow-hidden">
            <motion.div className="h-full bg-indigo-500" initial={{ width: 0 }} animate={{ width: `${progress}%` }} />
          </div>
          <p className="mt-6 text-[11px] font-black text-white/30 uppercase tracking-[0.4em]">Decoding Spatial Layers: {progress}%</p>
        </div>
      )}

      {/* Instruction Overlay */}
      {!selectedFrame && !loading && (
        <motion.div 
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="absolute bottom-10 left-1/2 -translate-x-1/2 px-8 py-4 bg-white/5 backdrop-blur-2xl border border-white/10 rounded-full z-10"
        >
          <p className="text-[10px] font-black text-white/60 uppercase tracking-[0.2em] flex items-center space-x-3">
             <Maximize className="h-4 w-4 text-indigo-400" />
             <span>Click any blue camera to view clinical photo layer</span>
          </p>
        </motion.div>
      )}
    </div>
  );
}
