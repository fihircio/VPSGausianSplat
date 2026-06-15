"use client";
import { useState, useEffect, useRef, use } from 'react';
import { useRouter } from 'next/navigation';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader.js';
import { Activity, ArrowLeft, Maximize, RotateCcw, Users, MapPin, Trash2, CheckCircle2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api, toApiStorageUrl, toApiWebSocketUrl } from '@/lib/api';
import { Scene, Frame, Anchor, ActiveAgent } from '@/types';
import AgentSidebar from '@/components/AgentSidebar';

// Important: import our new managers
import { TileManager } from '@/lib/TileManager';
import { GaussianSplatRenderer } from '@/lib/GaussianSplatRenderer';
import { AnchorManager } from '@/lib/AnchorManager';

// Fallback utility for classNames
const cn = (...classes: (string | undefined | null | false)[]) => classes.filter(Boolean).join(' ');

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

  // Anchor system properties
  const [anchorMode, setAnchorMode] = useState(false);
  const [pendingAnchor, setPendingAnchor] = useState<THREE.Vector3 | null>(null);
  const [anchorLabel, setAnchorLabel] = useState("");
  const [anchorGlbUrl, setAnchorGlbUrl] = useState("https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/main/2.0/Box/glTF-Binary/Box.glb");

  const agentsRef = useRef<Record<string, THREE.Group>>({});
  const agentsDataRef = useRef<ActiveAgent[]>([]);
  const router = useRouter();

  // Managers refs
  const anchorManagerRef = useRef<AnchorManager | null>(null);
  const tileManagerRef = useRef<TileManager | null>(null);
  const splatRendererRef = useRef<GaussianSplatRenderer | null>(null);

  useEffect(() => {
    api.getScene(id).then(setSceneData).catch(console.error);
    api.getSceneFrames(id).then(res => setFrames(res.frames)).catch(console.error);
  }, [id]);

  // Real-time Agent Sync via WebSocket
  useEffect(() => {
    if (!sceneData) return;
    
    const wsUrl = toApiWebSocketUrl(`/vps/ws/agents/${id}`);
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
    const dirLight = new THREE.DirectionalLight(0xffffff, 1);
    dirLight.position.set(5, 10, 7);
    scene.add(dirLight);

    // --- Interaction ---
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    const frustumObjects: THREE.Mesh[] = [];

    const loadSparsePointCloud = (url: string) =>
      new Promise<void>((resolve, reject) => {
        const loader = new PLYLoader();
        loader.load(
          url,
          (geometry) => {
            geometry.computeBoundingBox();
            const material = new THREE.PointsMaterial({
              size: 0.04,
              vertexColors: true,
              opacity: 0.9,
              transparent: true,
            });
            const points = new THREE.Points(geometry, material);
            points.userData = { isMapPointCloud: true };
            scene.add(points);
            resolve();
          },
          (event) => {
            if (event.lengthComputable) {
              setProgress(Math.round((event.loaded / event.total) * 100));
            }
          },
          reject
        );
      });

    // --- Initialization of Systems ---
    const initVisualizer = async () => {
      // 1. Initialize Anchor Manager
      const anchorMgr = new AnchorManager(id, scene);
      anchorManagerRef.current = anchorMgr;
      await anchorMgr.loadAnchors();
      setAnchors(anchorMgr.getAnchorsList());

      // 2. Initialize Map Representation (Splat vs Tiles)
      try {
        if (sceneData.splat_path) {
          const splatUrl = toApiStorageUrl(sceneData.splat_path);
          if (!splatUrl) throw new Error("Scene is missing a splat model URL");
          if (sceneData.splat_path.includes("sparse_points_fallback")) {
            await loadSparsePointCloud(splatUrl);
          } else {
            const splatRenderer = new GaussianSplatRenderer(scene, camera, renderer);
            splatRendererRef.current = splatRenderer;
            await splatRenderer.load(splatUrl, (p) => setProgress(p));
          }
        } else {
          // Fallback to Tile Streaming
          const tileMgr = new TileManager(id, scene);
          tileManagerRef.current = tileMgr;
          await tileMgr.init();
        }
      } catch (err) {
        console.error("Failed to inject 3D data pipeline:", err);
      }

      setLoading(false);
    };

    // --- Fit camera to the FULL scene bounding box (point cloud + frustums) ---
    const fitToScene = () => {
      const box = new THREE.Box3();
      scene.traverse((obj) => {
        // Skip helpers, grid, lights, and anchors
        if (obj instanceof THREE.GridHelper) return;
        if (obj instanceof THREE.AmbientLight || obj instanceof THREE.DirectionalLight) return;
        if (obj.userData?.isAnchor) return;
        if ((obj as THREE.Mesh).isMesh || (obj as THREE.Points).isPoints) {
          box.expandByObject(obj);
        }
      });

      if (!box.isEmpty()) {
        const center = new THREE.Vector3();
        box.getCenter(center);
        const size = new THREE.Vector3();
        box.getSize(size);
        const maxDim = Math.max(size.x, size.y, size.z);
        const camDist = Math.max(maxDim * 1.2, 3);

        controls.target.copy(center);
        camera.position.set(
          center.x + camDist * 0.7,
          center.y + camDist * 0.5,
          center.z + camDist * 0.7
        );
        grid.position.set(center.x, box.min.y - 0.1, center.z);
        controls.update();
      }
    };

    // Expose so UI button can call it
    (window as any).__vpsViewerFitToScene = fitToScene;

    initVisualizer();

    // --- Camera Poses (Frustum Cones) ---
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
        mesh.userData = { frame: f, isFrustum: true };
        scene.add(mesh);
        frustumObjects.push(mesh);
      });
    }

    // Phase 1: immediate rough centering on frustum centroid (fast)
    if (frustumObjects.length > 0) {
      const centroid = new THREE.Vector3();
      frustumObjects.forEach(obj => centroid.add(obj.position));
      centroid.divideScalar(frustumObjects.length);
      let maxDist = 0;
      frustumObjects.forEach(obj => { maxDist = Math.max(maxDist, obj.position.distanceTo(centroid)); });
      const camDist = Math.max(maxDist * 1.5, 3);
      controls.target.copy(centroid);
      camera.position.set(centroid.x + camDist, centroid.y + camDist * 0.6, centroid.z + camDist);
      grid.position.set(centroid.x, centroid.y - 0.5, centroid.z);
      controls.update();
    }

    // Phase 2: after PLY/splat fully loads, re-fit to the FULL scene bounding box
    setTimeout(() => { fitToScene(); }, 1800);

    // --- Events (Click & Raycasting) ---
    const handleClick = (event: MouseEvent) => {
      mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
      mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);

      if ((window as any).viewerAnchorMode) {
        // In anchor placement mode, try to hit points or meshes in the scene
        const intersects = raycaster.intersectObjects(scene.children, true);
        const hit = intersects.find(i => !i.object.userData.isFrustum && !i.object.userData.isAnchor);
        if (hit) {
          setPendingAnchor(hit.point);
        }
        return;
      }

      // Normal mode: check if we clicked a frame
      const intersects = raycaster.intersectObjects(frustumObjects);
      if (intersects.length > 0) {
        const frame = (intersects[0].object as any).userData.frame;
        setSelectedFrame(frame);
        frustumObjects.forEach(obj => ((obj as THREE.Mesh).material as THREE.MeshBasicMaterial).color.set(0x4f46e5));
        ((intersects[0].object as THREE.Mesh).material as THREE.MeshBasicMaterial).color.set(0xec4899);
      }
    };
    
    // Quick hack for enabling mode context within event listener
    window.addEventListener('click', handleClick);

    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', handleResize);

    const animate = () => {
      requestAnimationFrame(animate);
      
      // Update Systems
      if (tileManagerRef.current) tileManagerRef.current.update(camera);
      if (splatRendererRef.current) splatRendererRef.current.update();

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
      if (anchorManagerRef.current) anchorManagerRef.current.dispose();
      if (tileManagerRef.current) tileManagerRef.current.dispose();
      if (splatRendererRef.current) splatRendererRef.current.dispose();
      renderer.dispose();
      if (containerRef.current) containerRef.current.removeChild(renderer.domElement);
    };
  }, [sceneData, id, frames]);

  // Expose anchor mode safely
  useEffect(() => {
    (window as any).viewerAnchorMode = anchorMode;
  }, [anchorMode]);

  const handleConfirmAnchor = async () => {
    if (!pendingAnchor || !anchorManagerRef.current) return;
    try {
      await anchorManagerRef.current.createAnchor(pendingAnchor, anchorLabel || 'New Anchor', anchorGlbUrl);
      setAnchors(anchorManagerRef.current.getAnchorsList());
      setPendingAnchor(null);
      setAnchorMode(false);
      setAnchorLabel("");
    } catch (e) {
      alert("Failed to create anchor");
    }
  };

  const handleDeleteAnchor = async (anchorId: string) => {
    if (!anchorManagerRef.current) return;
    try {
      await anchorManagerRef.current.deleteAnchor(anchorId);
      setAnchors(anchorManagerRef.current.getAnchorsList());
    } catch (e) {
      alert("Failed to delete anchor");
    }
  };

  return (
    <div className="relative h-screen w-full bg-[#050505] overflow-hidden font-geist">
      {/* Header HUD */}
      <div className="absolute top-0 left-0 right-0 p-8 z-10 flex items-start justify-between pointer-events-none">
        <button onClick={() => router.back()} className="p-4 bg-white/5 backdrop-blur-3xl border border-white/10 rounded-3xl text-white hover:bg-white/10 transition-all pointer-events-auto shadow-2xl">
          <ArrowLeft className="h-6 w-6" />
        </button>
        <div className="flex items-start space-x-4">
          <button 
            onClick={() => setAnchorMode(!anchorMode)}
            className={cn(
              "p-4 backdrop-blur-3xl border rounded-3xl transition-all pointer-events-auto shadow-2xl group",
              anchorMode ? "bg-amber-500/20 border-amber-500/50 text-amber-400" : "bg-white/5 border-white/10 text-white hover:bg-white/10"
            )}
            title="Place Persistent AR Anchor"
          >
            <MapPin className={cn("h-6 w-6", anchorMode && "animate-pulse")} />
          </button>
          
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

      <div ref={containerRef} className="h-full w-full outline-none" />

      {/* Overlays / Sidebars */}
      <AgentSidebar isOpen={showAgents} agents={agents} />

      {/* Anchors Panel (Bottom Left) */}
      <div className="absolute bottom-8 left-8 w-64 max-h-[400px] overflow-y-auto pointer-events-auto z-20 space-y-2">
        {anchors.map(anchor => (
          <div key={anchor.id} className="p-3 bg-black/60 backdrop-blur-xl border border-white/10 rounded-xl flex items-center justify-between group">
            <div className="flex items-center space-x-3">
              <div className="p-1.5 bg-amber-500/10 rounded-md">
                <MapPin className="h-4 w-4 text-amber-400" />
              </div>
              <div>
                <p className="text-xs font-bold text-white">{anchor.label}</p>
                <p className="text-[10px] text-gray-500 font-mono mt-0.5">
                  {anchor.position.map(n => n.toFixed(1)).join(', ')}
                </p>
              </div>
            </div>
            <button 
              onClick={() => handleDeleteAnchor(anchor.id)}
              className="p-1 hover:bg-red-500/20 rounded text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>

      {/* Anchor Creation Modal */}
      <AnimatePresence>
        {anchorMode && pendingAnchor && (
          <motion.div 
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 20, opacity: 0 }}
            className="absolute bottom-20 left-1/2 -translate-x-1/2 w-[360px] bg-black/80 backdrop-blur-3xl border border-amber-500/30 rounded-3xl p-6 shadow-2xl z-40 pointer-events-auto"
          >
            <div className="flex items-center space-x-2 mb-4">
              <MapPin className="text-amber-400 h-5 w-5" />
              <h3 className="text-sm font-black text-white uppercase tracking-widest">New Spatial Anchor</h3>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="text-[10px] text-gray-400 uppercase font-bold block mb-1">Anchor Label</label>
                <input 
                  type="text" 
                  value={anchorLabel}
                  onChange={e => setAnchorLabel(e.target.value)}
                  placeholder="e.g. Infusion Pump A"
                  className="w-full bg-gray-900 border border-white/10 rounded-xl px-4 py-2 text-white text-sm focus:outline-none focus:border-amber-500"
                />
              </div>
              <div>
                <label className="text-[10px] text-gray-400 uppercase font-bold block mb-1">GLB Asset URL</label>
                <input 
                  type="text" 
                  value={anchorGlbUrl}
                  onChange={e => setAnchorGlbUrl(e.target.value)}
                  className="w-full bg-gray-900 border border-white/10 rounded-xl px-4 py-2 text-white text-sm font-mono focus:outline-none focus:border-amber-500"
                />
              </div>
              
              <div className="flex space-x-3 pt-2">
                <button 
                  onClick={() => setPendingAnchor(null)}
                  className="flex-1 py-2 rounded-xl text-xs font-bold text-gray-400 hover:bg-white/10 transition-colors uppercase tracking-widest"
                >
                  Cancel
                </button>
                <button 
                  onClick={handleConfirmAnchor}
                  className="flex-1 py-2 bg-amber-500 hover:bg-amber-400 text-black rounded-xl text-xs font-black transition-colors uppercase tracking-widest flex items-center justify-center space-x-1"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Lock Anchor</span>
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Frame Preview HUD (Bottom Middle) */}
      <AnimatePresence>
        {selectedFrame && !anchorMode && (
          <motion.div 
            initial={{ y: 200, x: '-50%', opacity: 0 }}
            animate={{ y: 0, x: '-50%', opacity: 1 }}
            exit={{ y: 200, x: '-50%', opacity: 0 }}
            className="absolute bottom-10 left-1/2 -translate-x-1/2 w-[400px] z-30"
          >
            <div className="glass-card overflow-hidden bg-black/60 border-indigo-500/30">
              <div className="relative aspect-video bg-gray-900">
                <img 
                  src={toApiStorageUrl(selectedFrame.image_path) ?? selectedFrame.image_path} 
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
      {!selectedFrame && !loading && !anchorMode && (
        <motion.div 
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="absolute bottom-10 left-1/2 -translate-x-1/2 px-8 py-4 bg-white/5 backdrop-blur-2xl border border-white/10 rounded-full z-10 pointer-events-none"
        >
          <p className="text-[10px] font-black text-white/60 uppercase tracking-[0.2em] flex items-center space-x-3">
             <Maximize className="h-4 w-4 text-indigo-400" />
             <span>Click any blue camera to view clinical photo layer</span>
          </p>
        </motion.div>
      )}

      {/* Fit to Scene Button — top left, always visible */}
      {!loading && (
        <motion.button
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          onClick={() => (window as any).__vpsViewerFitToScene?.()}
          className="absolute top-6 left-16 z-30 flex items-center space-x-2 px-4 py-2 bg-white/5 hover:bg-white/10 backdrop-blur-xl border border-white/10 hover:border-indigo-500/50 rounded-full transition-all text-white/60 hover:text-white"
          title="Fit camera to full scene"
        >
          <Maximize className="h-3.5 w-3.5" />
          <span className="text-[10px] font-black uppercase tracking-widest">Fit Scene</span>
        </motion.button>
      )}


      {/* Instruction Overlay Anchor Mode */}
      {anchorMode && !pendingAnchor && (
        <motion.div 
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="absolute bottom-10 left-1/2 -translate-x-1/2 px-8 py-4 bg-amber-500/20 backdrop-blur-2xl border border-amber-500/50 rounded-full z-10 pointer-events-none"
        >
          <p className="text-[10px] font-black text-amber-400 uppercase tracking-[0.2em] flex items-center space-x-3">
             <MapPin className="h-4 w-4" />
             <span>Click anywhere on the map to anchor a virtual object</span>
          </p>
        </motion.div>
      )}
    </div>
  );
}
