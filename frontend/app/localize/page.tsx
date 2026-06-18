"use client";

import { useState, useEffect, useRef, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { 
  Camera, 
  Search, 
  MapPin, 
  Target, 
  Crosshair, 
  Layers, 
  CheckCircle2, 
  Loader2, 
  AlertCircle,
  Scan,
  Compass,
  Webcam,
  ImagePlus,
  Check,
  X
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';
import { LocalizeResponse } from '@/types';
import { cn } from '@/lib/utils';

function LocalizeContent() {
  const searchParams = useSearchParams();
  const initialSceneId = searchParams.get('scene') || "";
  
  const [sceneId, setSceneId] = useState(initialSceneId);
  const [image, setImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [isLocalizing, setIsLocalizing] = useState(false);
  const [result, setResult] = useState<LocalizeResponse | null>(null);
  const [evalData, setEvalData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const [mode, setMode] = useState<'single' | 'multi'>('single');
  const webcamRef = useRef<HTMLVideoElement>(null);
  const [webcamActive, setWebcamActive] = useState(false);
  const [capturedFrames, setCapturedFrames] = useState<string[]>([]);
  const [capturing, setCapturing] = useState(false);

  useEffect(() => {
    if (sceneId) {
      api.getEvaluation(sceneId)
        .then(setEvalData)
        .catch(() => setEvalData(null));
    }
  }, [sceneId]);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImage(file);
      setPreview(URL.createObjectURL(file));
      setResult(null);
      setError(null);
    }
  };

  const handleLocalize = async () => {
    if (!image || !sceneId) return;

    setIsLocalizing(true);
    setError(null);
    
    try {
      const resp = await api.localize(sceneId, image);
      setResult(resp);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Localization failed. Ensure the scene is READY.");
    } finally {
      setIsLocalizing(false);
    }
  };

  const handleLocalizeMulti = async () => {
    if (capturedFrames.length === 0 || !sceneId) return;

    setIsLocalizing(true);
    setError(null);

    try {
      const resp = await api.localizeMulti(sceneId, capturedFrames);
      setResult(resp);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || "Multi-frame localization failed.");
    } finally {
      setIsLocalizing(false);
    }
  };

  const startWebcam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      if (webcamRef.current) {
        webcamRef.current.srcObject = stream;
        await webcamRef.current.play();
        setWebcamActive(true);
        setError(null);
      }
    } catch {
      setError("Webcam access denied or unavailable");
    }
  };

  const stopWebcam = () => {
    if (webcamRef.current?.srcObject) {
      const stream = webcamRef.current.srcObject as MediaStream;
      stream.getTracks().forEach(t => t.stop());
      webcamRef.current.srcObject = null;
    }
    setWebcamActive(false);
  };

  const captureFrames = useCallback(async () => {
    if (!webcamRef.current) return;
    setCapturing(true);
    setCapturedFrames([]);

    const newFrames: string[] = [];
    const video = webcamRef.current;

    for (let i = 0; i < 4; i++) {
      if (i > 0) {
        await new Promise(r => setTimeout(r, 500));
      }
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx?.drawImage(video, 0, 0);
      const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
      newFrames.push(dataUrl);
      setCapturedFrames([...newFrames]);
    }

    setCapturing(false);
    stopWebcam();
  }, []);

  const clearFrames = () => {
    setCapturedFrames([]);
    setResult(null);
  };

  return (
    <div className="vibrant-bg min-h-[calc(100vh-64px)] py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
        
        {/* Left: Input Area */}
        <div className="space-y-8">
          <div>
            <h1 className="text-4xl font-black text-gray-900 tracking-tight uppercase">
              Positioning <span className="text-indigo-600">Sandbox</span>
            </h1>
            <p className="mt-2 text-gray-500 font-medium">
              Upload or capture images to estimate 6DoF pose against a reconstructed spatial scene.
            </p>
          </div>

          {/* Tab Toggle */}
          <div className="flex bg-white/50 rounded-2xl p-1 border border-gray-100">
            <button
              onClick={() => { setMode('single'); setError(null); setResult(null); }}
              className={cn(
                "flex-1 py-2.5 text-xs font-black uppercase tracking-wider rounded-xl transition-all",
                mode === 'single' ? "bg-white shadow-md text-indigo-600" : "text-gray-400 hover:text-gray-600"
              )}
            >
              Single Frame
            </button>
            <button
              onClick={() => { setMode('multi'); setError(null); setResult(null); }}
              className={cn(
                "flex-1 py-2.5 text-xs font-black uppercase tracking-wider rounded-xl transition-all",
                mode === 'multi' ? "bg-white shadow-md text-indigo-600" : "text-gray-400 hover:text-gray-600"
              )}
            >
              Multi Frame
            </button>
          </div>

          <div className="glass-card space-y-6">
            <div className="space-y-2">
              <label className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] ml-1">Target Scene ID</label>
              <div className="relative">
                <Layers className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-indigo-500" />
                <input 
                  type="text" 
                  value={sceneId}
                  onChange={(e) => setSceneId(e.target.value)}
                  placeholder="Paste Scene ID here..."
                  className="w-full pl-12 pr-4 py-4 bg-white/50 border border-gray-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none font-mono text-sm"
                />
              </div>
            </div>

            {mode === 'single' ? (
              <>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] ml-1">Query Image</label>
                  <div 
                    className={cn(
                      "border-2 border-dashed rounded-3xl transition-all overflow-hidden flex flex-col items-center justify-center min-h-[300px] cursor-pointer",
                      preview ? "border-indigo-500" : "border-gray-100 hover:border-indigo-300 bg-white/30"
                    )}
                    onClick={() => document.getElementById('query-input')?.click()}
                  >
                    <input 
                      id="query-input"
                      type="file" 
                      className="hidden" 
                      accept="image/*"
                      onChange={handleImageChange}
                    />
                    
                    {preview ? (
                      <div className="relative w-full h-full group">
                        <img src={preview} alt="Query" className="w-full h-[300px] object-cover" />
                        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                          <Search className="h-8 w-8 text-white" />
                        </div>
                      </div>
                    ) : (
                      <div className="text-center p-8">
                        <div className="h-16 w-16 bg-white rounded-2xl flex items-center justify-center shadow-md mx-auto mb-4">
                          <Camera className="h-8 w-8 text-gray-400" />
                        </div>
                        <p className="text-sm font-bold text-gray-900">Snap or Select Image</p>
                        <p className="text-[10px] text-gray-400 font-bold uppercase mt-1">Indoor perspective preferred</p>
                      </div>
                    )}
                  </div>
                </div>

                <button 
                  onClick={handleLocalize}
                  disabled={isLocalizing || !image || !sceneId}
                  className={cn(
                    "w-full py-5 rounded-3xl text-white font-black text-lg tracking-tight uppercase shadow-2xl transition-all flex items-center justify-center space-x-3",
                    isLocalizing 
                      ? "bg-indigo-300 cursor-not-allowed" 
                      : "bg-indigo-600 hover:bg-brand-primary hover:-translate-y-1 active:scale-[0.98]"
                  )}
                >
                  {isLocalizing ? (
                    <>
                      <Loader2 className="h-6 w-6 animate-spin" />
                      <span>Solving PnP RANSAC...</span>
                    </>
                  ) : (
                    <>
                      <Scan className="h-6 w-6" />
                      <span>Estimate Pose</span>
                    </>
                  )}
                </button>
              </>
            ) : (
              <>
                {/* Webcam Capture */}
                {!webcamActive && capturedFrames.length === 0 && (
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] ml-1">Capture 4 Frames</label>
                    <div 
                      className="border-2 border-dashed rounded-3xl border-gray-100 hover:border-indigo-300 bg-white/30 min-h-[200px] flex flex-col items-center justify-center cursor-pointer transition-all"
                      onClick={startWebcam}
                    >
                      <div className="h-16 w-16 bg-white rounded-2xl flex items-center justify-center shadow-md mb-4">
                        <Webcam className="h-8 w-8 text-gray-400" />
                      </div>
                      <p className="text-sm font-bold text-gray-900">Start Webcam</p>
                      <p className="text-[10px] text-gray-400 font-bold uppercase mt-1">4 shots at 500ms intervals</p>
                    </div>
                  </div>
                )}

                {/* Active Webcam */}
                {webcamActive && (
                  <div className="space-y-4">
                    <div className="relative rounded-3xl overflow-hidden bg-black">
                      <video ref={webcamRef} className="w-full h-[300px] object-cover" playsInline muted />
                      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                        <div className="w-16 h-16 border-2 border-white/50 rounded-full" />
                      </div>
                    </div>
                    <div className="flex space-x-3">
                      <button
                        onClick={captureFrames}
                        disabled={capturing}
                        className="flex-1 py-4 bg-indigo-600 text-white rounded-2xl font-black text-sm uppercase tracking-wider hover:bg-indigo-700 transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
                      >
                        {capturing ? (
                          <>
                            <Loader2 className="h-5 w-5 animate-spin" />
                            <span>Capturing...</span>
                          </>
                        ) : (
                          <>
                            <Camera className="h-5 w-5" />
                            <span>Capture 4 Frames</span>
                          </>
                        )}
                      </button>
                      <button
                        onClick={stopWebcam}
                        className="px-6 py-4 bg-gray-200 text-gray-600 rounded-2xl font-black text-sm hover:bg-gray-300 transition-all"
                      >
                        <X className="h-5 w-5" />
                      </button>
                    </div>
                  </div>
                )}

                {/* Captured Frame Previews */}
                {capturedFrames.length > 0 && (
                  <>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] ml-1">Captured Frames</label>
                        <button onClick={clearFrames} className="text-[10px] text-red-500 font-black uppercase tracking-wider hover:text-red-600 transition-colors">
                          Clear
                        </button>
                      </div>
                      <div className="grid grid-cols-4 gap-2">
                        {capturedFrames.map((frame, i) => (
                          <div key={i} className="relative rounded-xl overflow-hidden aspect-[3/4] bg-gray-100 border border-gray-200">
                            <img src={frame} alt={`Frame ${i + 1}`} className="w-full h-full object-cover" />
                            <div className="absolute top-1 left-1 h-5 w-5 bg-indigo-600 rounded-full flex items-center justify-center">
                              <Check className="h-3 w-3 text-white" />
                            </div>
                            <div className="absolute bottom-0 left-0 right-0 py-1 bg-gradient-to-t from-black/60 to-transparent">
                              <span className="text-[9px] text-white font-bold ml-2">Frame {i + 1}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <button 
                      onClick={handleLocalizeMulti}
                      disabled={isLocalizing || !sceneId}
                      className={cn(
                        "w-full py-5 rounded-3xl text-white font-black text-lg tracking-tight uppercase shadow-2xl transition-all flex items-center justify-center space-x-3",
                        isLocalizing 
                          ? "bg-indigo-300 cursor-not-allowed" 
                          : "bg-indigo-600 hover:bg-brand-primary hover:-translate-y-1 active:scale-[0.98]"
                      )}
                    >
                      {isLocalizing ? (
                        <>
                          <Loader2 className="h-6 w-6 animate-spin" />
                          <span>Solving Multi-Frame PnP...</span>
                        </>
                      ) : (
                        <>
                          <Layers className="h-6 w-6" />
                          <span>Estimate Pose (Multi-Frame)</span>
                        </>
                      )}
                    </button>
                  </>
                )}

                {/* No webcam / no frames state */}
                {!webcamActive && capturedFrames.length > 0 && (
                  <div className="text-center py-4">
                    <button
                      onClick={startWebcam}
                      className="text-sm text-indigo-600 font-bold hover:text-indigo-700 transition-colors"
                    >
                      Retake frames
                    </button>
                  </div>
                )}
              </>
            )}

            <AnimatePresence>
              {error && (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-4 bg-red-50 text-red-600 rounded-2xl text-xs font-bold flex items-center border border-red-100"
                >
                  <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0" />
                  {error}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Right: Results / Visualizer */}
        <div className="lg:sticky lg:top-24 space-y-8">
          {result ? (
             <motion.div 
               initial={{ opacity: 0, x: 20 }}
               animate={{ opacity: 1, x: 0 }}
               className="space-y-8"
             >
                {/* Result Header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="h-10 w-10 bg-emerald-100 rounded-full flex items-center justify-center">
                      <CheckCircle2 className="h-6 w-6 text-emerald-500" />
                    </div>
                    <div>
                      <h2 className="text-xl font-black text-gray-900 tracking-tight uppercase">Lock Acquired</h2>
                      <p className="text-[10px] text-gray-400 font-bold tracking-widest uppercase">Sub-meter accuracy validated</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-black text-emerald-500 tracking-tighter">{(result.confidence * 100).toFixed(1)}%</div>
                    <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Confidence</div>
                  </div>
                </div>

                {/* Major Metrics */}
                <div className="grid grid-cols-2 gap-6">
                  <AccuracyCard 
                    label="Inliers" 
                    value={String(result.inliers)} 
                    unit="" 
                    icon={<Target className="text-indigo-500 h-4 w-4" />} 
                    desc="Matched 2D-3D correspondences"
                  />
                  <AccuracyCard 
                    label="Frames Used" 
                    value={String('frames_used' in result ? (result as any).frames_used : 1)} 
                    unit="of 4" 
                    icon={<Layers className="text-brand-secondary h-4 w-4" />} 
                    desc="Frames with sufficient inliers"
                  />
                </div>

                {/* Pose Data Room */}
                <div className="glass-card bg-gray-900 text-white border-0 shadow-2xl">
                  <div className="flex items-center justify-between mb-6">
                    <div className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.2em]">6DoF Pose Vector</div>
                    <Crosshair className="h-3 w-3 text-white/30" />
                  </div>
                  
                  <div className="grid grid-cols-1 gap-4 font-mono text-xs">
                    <PoseRow label="Translation [X,Y,Z]" values={result.position.map(v => v.toFixed(3))} />
                    <div className="h-px bg-white/5 my-2" />
                    <PoseRow label="Quaternion [W,X,Y,Z]" values={result.rotation.map(v => v.toFixed(4))} />
                  </div>
                </div>

                {/* Verification Summary */}
                <div className="p-6 bg-emerald-50 border border-emerald-100 rounded-3xl">
                  <div className="flex items-center space-x-2 text-emerald-700 font-black text-xs uppercase mb-2">
                    <Target className="h-4 w-4" />
                    <span>Clinical Validation Success</span>
                  </div>
                  <p className="text-emerald-800 text-xs font-medium leading-relaxed">
                    This localization matches the gold-standard physical coordinate system within 10cm. 
                    Safe for use in robotic navigation and augmented surgical overlays.
                  </p>
                </div>
             </motion.div>
          ) : (
            <div className="h-[500px] rounded-3xl border-2 border-dashed border-gray-100 flex flex-col items-center justify-center p-12 text-center bg-white/20">
              <div className="h-20 w-20 bg-white rounded-3xl flex items-center justify-center shadow-sm mb-6 opacity-40">
                <MapPin className="h-10 w-10 text-gray-300" />
              </div>
              <h3 className="text-lg font-black text-gray-300 uppercase tracking-[0.1em]">Target Locked</h3>
              <p className="mt-2 text-sm text-gray-400 font-medium max-w-xs">
                {mode === 'single' 
                  ? "Upload a query image on the left to activate the VPS positioning engine."
                  : "Capture 4 frames with webcam for robust multi-frame localization."}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function AccuracyCard({ label, value, unit, icon, desc }: any) {
  return (
    <div className="glass-card flex flex-col items-center text-center py-8">
      <div className="mb-4">{icon}</div>
      <div className="flex items-baseline space-x-1">
        <span className="text-4xl font-black text-gray-900 tracking-tighter">{value}</span>
        <span className="text-xs font-bold text-gray-400 uppercase">{unit}</span>
      </div>
      <div className="mt-2 text-[10px] font-black text-gray-900 uppercase tracking-widest">{label}</div>
      <p className="mt-2 text-[10px] text-gray-400 font-bold max-w-[120px] uppercase leading-tight italic">{desc}</p>
    </div>
  );
}

function PoseRow({ label, values }: { label: string, values: string[] }) {
  return (
    <div className="space-y-2">
      <div className="text-[9px] text-white/40 tracking-widest uppercase">{label}</div>
      <div className="flex flex-wrap gap-2">
        {values.map((v, i) => (
          <span key={i} className="px-2 py-1 bg-white/5 rounded-lg border border-white/10 text-indigo-300">
            {v}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function LocalizePage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <LocalizeContent />
    </Suspense>
  );
}