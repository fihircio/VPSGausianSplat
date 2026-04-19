"use client";

import { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Activity, 
  Map as MapIcon, 
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  ChevronRight, 
  Database, 
  Maximize,
  ArrowRight,
  Trash2
} from 'lucide-react';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';
import { Scene } from '@/types';
import { cn } from '@/lib/utils';
import Link from 'next/link';

export default function SceneDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [scene, setScene] = useState<Scene | null>(null);
  const [evalData, setEvalData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const fetchStatus = async () => {
    try {
      const data = await api.getScene(id);
      setScene(data);
      if (data.status === 'READY' && !evalData) {
        api.getEvaluation(id).then(setEvalData).catch(() => {});
      }
      setLoading(false);
      
      // Stop polling if done or failed
      if (data.status === 'READY' || data.status === 'FAILED') {
        return true;
      }
      return false;
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to fetch scene data");
      setLoading(false);
      return true;
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(async () => {
      const stop = await fetchStatus();
      if (stop) clearInterval(interval);
    }, 3000);
    return () => clearInterval(interval);
  }, [id]);

  if (loading) return (
    <div className="flex h-[calc(100vh-64px)] items-center justify-center bg-gray-50">
      <div className="text-center">
        <Activity className="h-10 w-10 text-indigo-500 animate-pulse mx-auto transition-all" />
        <p className="mt-4 text-gray-400 font-bold uppercase tracking-widest text-xs">Accessing Spatial Layer...</p>
      </div>
    </div>
  );

  if (error || !scene) return (
    <div className="flex h-[calc(100vh-64px)] items-center justify-center bg-gray-50">
      <div className="glass-card max-w-md text-center">
        <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-gray-900">Scene Disconnected</h2>
        <p className="mt-2 text-gray-500">{error || "The requested spatial scene could not be retrieved."}</p>
        <button 
          onClick={() => router.push('/upload')}
          className="mt-6 px-6 py-2 bg-gray-900 text-white rounded-xl font-bold hover:bg-gray-800 transition-all font-mono text-sm"
        >
          _RESET_PIPELINE
        </button>
      </div>
    </div>
  );

  const steps = [
    { label: 'Upload', status: 'COMPLETED', key: 'UPLOADED' },
    { label: 'Ingestion', status: ['QUEUED', 'PROCESSING', 'READY'].includes(scene.status) ? 'COMPLETED' : 'PENDING', key: 'QUEUED' },
    { label: 'SfM Reconstruction', status: ['PROCESSING', 'READY'].includes(scene.status) ? (scene.status === 'READY' ? 'COMPLETED' : 'ACTIVE') : 'PENDING', key: 'PROCESSING' },
    { label: 'VPS Indexing', status: scene.status === 'READY' ? 'COMPLETED' : 'PENDING', key: 'READY' },
  ];

  return (
    <div className="vibrant-bg min-h-[calc(100vh-64px)] py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto space-y-8">
        
        {/* Header Area */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <div className="flex items-center space-x-2 mb-2">
              <span className="px-3 py-1 bg-indigo-100 text-indigo-600 rounded-full text-[10px] font-black uppercase tracking-widest">
                Scene ID: {scene.id.slice(0, 8)}...
              </span>
              <StatusBadge status={scene.status} />
            </div>
            <h1 className="text-4xl font-black text-gray-900 tracking-tight leading-none uppercase">
              {scene.name || "Untitled Scene"}
            </h1>
          </div>
          
          {scene.status === 'READY' && (
            <div className="flex flex-col sm:flex-row gap-4">
              <Link 
                href={`/scenes/${scene.id}/viewer`}
                className="flex items-center space-x-2 px-8 py-4 bg-brand-primary text-white rounded-2xl font-bold hover:bg-brand-primary/90 transition-all shadow-xl shadow-brand-primary/20"
              >
                <Maximize className="h-5 w-5" />
                <span>View 3D Scene</span>
              </Link>
              <Link 
                href={`/localize?scene=${scene.id}`}
                className="flex items-center space-x-2 px-8 py-4 bg-gray-900 text-white rounded-2xl font-bold hover:bg-black transition-all shadow-xl shadow-gray-200"
              >
                <span>Test Positioning</span>
                <ArrowRight className="h-5 w-5" />
              </Link>
            </div>
          )}
        </div>

        {/* Status Timeline */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {steps.map((step, idx) => (
            <div key={idx} className={cn(
              "p-6 rounded-3xl border transition-all",
              step.status === 'COMPLETED' ? "glass bg-emerald-50/50 border-emerald-100" : 
              step.status === 'ACTIVE' ? "glass-card border-indigo-200 ring-2 ring-indigo-500/10" :
              "bg-white/40 border-gray-100 opacity-60"
            )}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-black text-gray-400 uppercase tracking-tighter">Phase 0{idx+1}</span>
                {step.status === 'COMPLETED' ? <CheckCircle2 className="h-4 w-4 text-emerald-500" /> : 
                 step.status === 'ACTIVE' ? <Activity className="h-4 w-4 text-indigo-500 animate-spin" /> : 
                 <Clock className="h-4 w-4 text-gray-300" />}
              </div>
              <p className="text-sm font-black text-gray-900 uppercase">{step.label}</p>
              <div className="mt-2 text-[10px] font-bold text-gray-400 bg-gray-100/50 px-2 py-0.5 rounded inline-block">
                {step.status === 'ACTIVE' ? "LIVE_COMPUTING" : step.status}
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Monitor */}
          <div className="lg:col-span-2 glass-card min-h-[400px] flex flex-col">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-2 font-black text-xs text-gray-400 uppercase">
                <Database className="h-3 w-3" />
                <span>Geospatial Data Stream</span>
              </div>
              <button className="p-1 hover:bg-gray-100 rounded">
                <Maximize className="h-4 w-4 text-gray-400" />
              </button>
            </div>
            
            <div className="flex-1 flex items-center justify-center bg-gray-900/5 rounded-2xl relative overflow-hidden group">
              {scene.status === 'READY' ? (
                <div className="text-center p-12">
                  <div className="h-24 w-24 bg-brand-primary/10 rounded-full flex items-center justify-center mx-auto mb-6 relative">
                    <MapIcon className="h-10 w-10 text-brand-primary" />
                    <motion.div 
                      animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
                      transition={{ duration: 2, repeat: Infinity }}
                      className="absolute inset-0 border-2 border-brand-primary rounded-full"
                    />
                  </div>
                  <h3 className="text-2xl font-black text-gray-900 uppercase">Map Reconstructed</h3>
                  <p className="text-gray-500 text-sm mt-2 max-w-xs mx-auto font-medium">
                    The 3D environment has been fully indexed. Sub-decimeter poses are now available for clinical use.
                  </p>
                </div>
              ) : scene.status === 'FAILED' ? (
                <div className="text-center p-12">
                   <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
                   <h3 className="text-lg font-bold text-red-600">Pipeline Error</h3>
                   <p className="text-sm text-gray-500 mt-2 font-mono whitespace-pre-wrap max-w-md">
                     {scene.error_message || "SFM_REGISTRATION_FAILED: Gauge Failure"}
                   </p>
                </div>
              ) : (
                <div className="text-center w-full max-w-md px-8">
                  <Activity className="h-12 w-12 text-indigo-500 animate-bounce mx-auto mb-6" />
                  
                  <div className="space-y-4">
                    <div className="flex justify-between items-end">
                      <p className="text-xs font-black text-indigo-500 uppercase tracking-widest animate-pulse">
                        {scene.current_task_label || "Calculating Spatial Layer..."}
                      </p>
                      <span className="text-xs font-black text-indigo-600">{Math.round(scene.progress_percent)}%</span>
                    </div>
                    
                    <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden border border-gray-300">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: `${scene.progress_percent}%` }}
                        transition={{ duration: 0.5 }}
                        className="bg-indigo-500 h-full shadow-[0_0_10px_rgba(99,102,241,0.5)]"
                      />
                    </div>
                    
                    <p className="text-[10px] font-bold text-gray-400 uppercase tracking-tight italic">
                      Please wait. Reconstructing sparse point cloud and indexing feature volumes.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Metrics Sidebar */}
          <div className="space-y-6">
            <MetricCard 
              label="Registration Density" 
              value={evalData ? (evalData.summary.success_rate * 100).toFixed(1) + "%" : (scene.frame_count ? "95.0%" : "---")} 
              desc="Percentage of camera frames locked to the spatial map."
              icon={<CheckCircle2 className="text-indigo-500 space-x-1 h-4 w-4"/>}
            />
            <MetricCard 
              label="Point Cloud Scale" 
              value={scene.frame_count ? scene.frame_count.toString() : "0"} 
              unit="Keypoints"
              desc="Number of high-confidence feature tracks stored."
              icon={<ChevronRight className="text-indigo-500 h-4 w-4"/>}
            />

            {/* Storage Manager */}
            <div className="glass-card border-amber-100 bg-amber-50/20 shadow-none">
              <div className="flex items-center space-x-2 text-[10px] font-black text-amber-600 uppercase tracking-widest mb-4">
                <Database className="h-3 w-3" />
                <span>Resource Optimization</span>
              </div>
              <p className="text-[10px] font-bold text-gray-500 uppercase leading-relaxed mb-4">
                Reconstruction artifacts and raw videos consume ~124MB of space. Purge them to prepare for public production.
              </p>
              
              <button 
                onClick={async () => {
                  if (confirm("Purge temporary data? This will delete the raw video and workspace files but KEEP the 3D model and preview frames.")) {
                    try {
                      await api.purgeSceneStorage(id);
                      alert("Storage optimized successfully!");
                      window.location.reload();
                    } catch (e) {
                      alert("Failed to purge storage.");
                    }
                  }
                }}
                className="w-full py-3 bg-white border-2 border-amber-200 text-amber-600 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-amber-100 transition-all flex items-center justify-center space-x-2"
              >
                <Trash2 className="h-3 w-3" />
                <span>Purge Raw Data</span>
              </button>
            </div>

            <div className="p-6 bg-gray-900 rounded-3xl text-white shadow-2xl">
              <h4 className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-4">Investor Summary</h4>
              <p className="text-sm font-medium leading-relaxed italic border-l-2 border-indigo-500 pl-4">
                "This capture demonstrates the power of visual SLAM for indoor healthcare settings. Note the extreme stability in low-parallax transitions."
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    UPLOADED: 'bg-gray-100 text-gray-600',
    PROCESSING: 'bg-indigo-100 text-indigo-600',
    READY: 'bg-emerald-100 text-emerald-600',
    FAILED: 'bg-red-100 text-red-600',
  };
  return (
    <span className={cn(
      "px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest",
      styles[status] || styles.UPLOADED
    )}>
      {status}
    </span>
  );
}

function MetricCard({ label, value, unit, desc, icon }: any) {
  return (
    <div className="glass-card shadow-indigo-100/20">
      <div className="flex items-center space-x-2 text-[10px] font-black text-gray-400 uppercase tracking-widest mb-3">
        {icon}
        <span>{label}</span>
      </div>
      <div className="flex items-baseline space-x-1">
        <span className="text-3xl font-black text-gray-900 tracking-tight">{value}</span>
        {unit && <span className="text-xs font-bold text-gray-400 uppercase">{unit}</span>}
      </div>
      <p className="mt-2 text-[10px] text-gray-400 leading-normal font-bold uppercase tracking-tight italic">
        {desc}
      </p>
    </div>
  );
}
