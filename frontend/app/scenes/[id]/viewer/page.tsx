"use client";

import { useState, useEffect, useRef, use } from 'react';
import { useRouter } from 'next/navigation';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader.js';
import { Activity, ArrowLeft, Maximize, RotateCcw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';
import { Scene, Frame, Anchor, ActiveAgent } from '@/types';
import AgentSidebar from '@/components/AgentSidebar';
import { Users } from 'lucide-react';

export default function SceneViewerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const containerRef = useRef<HTMLDivElement>(null);
  const [sceneData, setSceneData] = useState<Scene | null>(null);
  const [frames, setFrames] = useState<Frame[]>([]);
  const [anchors, setAnchors] = useState<Anchor[]>([]);
  const [agents, setAgents] = useState<ActiveAgent[]>([]);
  const [showAgents, setShowAgents] = useState(false);
  const [selectedFrame, setSelectedFrame] = useState<Frame | null>(null);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(0);
  
  const agentsRef = useRef<Record<string, THREE.Group>>({});
  const agentsDataRef = useRef<ActiveAgent[]>([]);
  const anchorsDataRef = useRef<Anchor[]>([]);
  const router = useRouter();

  useEffect(() => {
    api.getScene(id).then(setSceneData).catch(console.error);
    api.getSceneFrames(id).then(res => setFrames(res.frames)).catch(console.error);
    api.listAnchors(id).then(data => {
      setAnchors(data);
      anchorsDataRef.current = data;
    }).catch(console.error);
  }, [id]);

  // Real-time Agent Sync via WebSocket
  useEffect(() => {
    if (!sceneData) return;
    
    const wsUrl = `ws://localhost:8000/vps/ws/agents/${id}`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'agent_update') {
          setAgents(prev => {
            const index = prev.findIndex(a => a.id === data.agent_id);
            const updatedAgent: ActiveAgent = {
              id: data.agent_id,
              name: data.name || "Remote Agent",
              role: data.role || "Clinician",
              position: data.position,
              rotation: data.rotation,
              last_seen: new Date().toISOString()
            };

            let next;
            if (index >= 0) {
              next = [...prev];
              next[index] = updatedAgent;
            } else {
              next = [...prev, updatedAgent];
            }
            agentsDataRef.current = next;
            return next;
          });
        }
      } catch (err) {
        console.error("WS Message Error:", err);
      }
    };

    ws.onopen = () => console.log("Spatial Sync Connected");
    ws.onclose = () => console.log("Spatial Sync Disconnected");

    return () => ws.close();
  }, [sceneData, id]);

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

    // --- Anchors ---
    const renderAnchors = () => {
      anchorsDataRef.current.forEach(a => {
        const pinGeom = new THREE.SphereGeometry(0.08, 16, 16);
        const pinMat = new THREE.MeshStandardMaterial({ 
          color: 0xec4899, 
          emissive: 0xec4899,
          emissiveIntensity: 1.0
        });
        const pin = new THREE.Mesh(pinGeom, pinMat);
        pin.position.set(a.position[0], a.position[1], a.position[2]);
        
        const ringGeom = new THREE.RingGeometry(0.12, 0.14, 32);
        ringGeom.rotateX(-Math.PI/2);
        const ring = new THREE.Mesh(ringGeom, pinMat);
        ring.position.set(a.position[0], a.position[1], a.position[2]);
        
        scene.add(pin);
        scene.add(ring);
      });
    };
    renderAnchors();

    const animate = () => {
      requestAnimationFrame(animate);
      
      // Update Agents from Ref
      agentsDataRef.current.forEach(agent => {
        let group = agentsRef.current[agent.id];
        if (!group) {
          group = new THREE.Group();
          const markerGeom = new THREE.CylinderGeometry(0, 0.1, 0.3, 4);
          const markerMat = new THREE.MeshBasicMaterial({ color: 0x4f46e5 });
          const marker = new THREE.Mesh(markerGeom, markerMat);
          marker.rotation.x = Math.PI / 2;
          
          const ring = new THREE.Mesh(
            new THREE.RingGeometry(0.2, 0.22, 32),
            new THREE.MeshBasicMaterial({ color: 0x4f46e5, transparent: true, opacity: 0.5 })
          );
          ring.rotation.x = -Math.PI / 2;
          
          group.add(marker);
          group.add(ring);
          scene.add(group);
          agentsRef.current[agent.id] = group;
        }
        
        // Smoothly move towards target
        group.position.lerp(new THREE.Vector3(agent.position[0], agent.position[1], agent.position[2]), 0.1);
      });

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
        <div className="flex items-start space-x-4">
          <button 
            onClick={() => setShowAgents(!showAgents)} 
            className={cn(
              "p-4 backdrop-blur-3xl border rounded-3xl transition-all pointer-events-auto shadow-2xl",
              showAgents ? "bg-indigo-500/20 border-indigo-500/50 text-indigo-400" : "bg-white/5 border-white/10 text-white hover:bg-white/10"
            )}
          >
            <Users className="h-6 w-6" />
          </button>
          <div className="text-right">
            <div className="px-4 py-1.5 bg-indigo-500/10 border border-indigo-500/20 rounded-full inline-block backdrop-blur-xl">
               <span className="text-indigo-400 text-[10px] font-black uppercase tracking-[0.2em]">Clinical Visualizer 2.0</span>
            </div>
            <h1 className="mt-4 text-4xl font-black text-white uppercase tracking-tighter">{sceneData?.name || "Initializing..."}</h1>
          </div>
        </div>
      </div>

      <div ref={containerRef} className="h-full w-full" />

      <AgentSidebar isOpen={showAgents} agents={agents} />

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
