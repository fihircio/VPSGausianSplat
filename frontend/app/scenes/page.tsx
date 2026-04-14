"use client";

import { useState, useEffect } from 'react';
import { 
  Map as MapIcon, 
  ChevronRight, 
  Maximize, 
  Clock, 
  CheckCircle2, 
  AlertTriangle,
  Activity,
  ArrowRight
} from 'lucide-react';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';
import { Scene } from '@/types';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export default function SpatialGalleryPage() {
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listScenes()
      .then(setScenes)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-[calc(100vh-64px)] items-center justify-center bg-gray-50/50">
        <div className="text-center">
            <Activity className="h-10 w-10 text-brand-primary animate-pulse mx-auto" />
            <p className="mt-4 text-xs font-black text-gray-400 uppercase tracking-widest">Accessing Spatial Library...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="vibrant-bg min-h-[calc(100vh-64px)] py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-12">
            <h1 className="text-5xl font-black text-gray-900 tracking-tighter uppercase leading-none mb-4">
                Spatial <span className="text-brand-primary">Explorer</span>
            </h1>
            <p className="max-w-2xl text-lg text-gray-500 font-medium">
                Explore high-fidelity 3D digital twins of our hospital infrastructure. Select a location to enter the immersive mapping layer.
            </p>
        </div>

        {scenes.length === 0 ? (
            <div className="glass-card p-24 text-center">
                <MapIcon className="h-16 w-16 text-gray-200 mx-auto mb-6" />
                <h3 className="text-xl font-bold text-gray-900 uppercase">No Spatial Maps Yet</h3>
                <p className="text-gray-500 mt-2">Start by uploading a video of a floor or room.</p>
                <Link 
                    href="/upload"
                    className="mt-6 inline-flex items-center space-x-2 px-6 py-3 bg-gray-900 text-white rounded-2xl font-bold hover:bg-black transition-all"
                >
                    <span>Begin Mapping</span>
                    <ArrowRight className="h-4 w-4" />
                </Link>
            </div>
        ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {scenes.map((scene, idx) => (
                    <SceneCard key={scene.id} scene={scene} index={idx} />
                ))}
            </div>
        )}
      </div>
    </div>
  );
}

function SceneCard({ scene, index }: { scene: Scene, index: number }) {
  const isReady = scene.status === 'READY';
  
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="glass-card group hover:scale-[1.02] transition-all duration-300 flex flex-col h-full bg-white/70"
    >
      <div className="flex-1">
        <div className="flex items-center justify-between mb-6">
            <div className="h-10 w-10 bg-gray-100 rounded-xl flex items-center justify-center text-gray-400 group-hover:bg-brand-primary/10 group-hover:text-brand-primary transition-colors">
                <MapIcon className="h-5 w-5" />
            </div>
            <StatusBadge status={scene.status} />
        </div>
        
        <h3 className="text-2xl font-black text-gray-900 uppercase tracking-tight mb-2 truncate">
            {scene.name}
        </h3>
        
        <div className="flex items-center space-x-4 text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-6 border-b border-gray-100 pb-4">
            <div className="flex items-center space-x-1">
                <Clock className="h-3 w-3" />
                <span>{new Date(scene.created_at).toLocaleDateString()}</span>
            </div>
            <div className="flex items-center space-x-1">
                <Maximize className="h-3 w-3" />
                <span>{scene.frame_count || 0} Points</span>
            </div>
        </div>
      </div>

      <div className="space-y-3 pt-6">
          <Link 
            href={`/scenes/${scene.id}`}
            className="flex items-center justify-between w-full px-5 py-3 bg-gray-100 hover:bg-gray-200 rounded-2xl text-xs font-black text-gray-600 transition-all uppercase tracking-widest"
          >
            <span>Telemetry Details</span>
            <ChevronRight className="h-4 w-4" />
          </Link>
          
          {isReady && (
            <Link 
                href={`/scenes/${scene.id}/viewer`}
                className="flex items-center justify-center space-x-2 w-full px-5 py-4 bg-gray-900 text-white rounded-2xl text-xs font-black hover:bg-black transition-all shadow-xl shadow-gray-200"
            >
                <Maximize className="h-4 w-4" />
                <span>ENTER 3D VIEWER</span>
            </Link>
          )}
      </div>
    </motion.div>
  );
}

function StatusBadge({ status }: { status: string }) {
    const styles: Record<string, string> = {
      UPLOADED: 'bg-gray-100 text-gray-600',
      QUEUED: 'bg-amber-100 text-amber-600',
      PROCESSING: 'bg-indigo-100 text-indigo-600',
      READY: 'bg-emerald-100 text-emerald-600',
      FAILED: 'bg-red-100 text-red-600',
    };
    return (
      <span className={cn(
        "px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-widest",
        styles[status] || styles.UPLOADED
      )}>
        {status}
      </span>
    );
}
