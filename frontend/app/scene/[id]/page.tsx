"use client";

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { api } from '@/lib/api';
import { Scene } from '@/types';
import { formatDate } from '@/lib/utils';
import SceneStatusTimeline from '@/components/SceneStatusTimeline';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'; // We'll create a simple version or use basic divs
import { Database, Image as ImageIcon, Box, Activity, AlertCircle, Info } from 'lucide-react';

export default function MonitorPage() {
  const { id } = useParams();
  const [scene, setScene] = useState<Scene | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;

    const fetchScene = async () => {
      try {
        const data = await api.getScene(id as string);
        setScene(data);
        if (data.status === 'READY' || data.status === 'FAILED') {
          clearInterval(interval);
        }
      } catch (err) {
        setError('Failed to fetch scene status.');
      }
    };

    fetchScene();
    const interval = setInterval(fetchScene, 3000);
    return () => clearInterval(interval);
  }, [id]);

  if (!scene) {
    return (
      <div className="flex items-center justify-center p-20">
        <Activity className="h-10 w-10 text-indigo-600 animate-pulse mr-3" />
        <span className="text-xl font-semibold text-gray-700">Loading scene metrics...</span>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto py-12 px-4 space-y-8">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{scene.name}</h1>
          <p className="text-gray-500 font-mono text-sm mt-1">{scene.id}</p>
        </div>
        <div className="text-right">
          <p className="text-sm font-medium text-gray-400">CREATED AT</p>
          <p className="text-gray-900 font-semibold">{formatDate(scene.created_at)}</p>
        </div>
      </div>

      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
        <h2 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-6">Pipeline Progress</h2>
        <SceneStatusTimeline status={scene.status} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <DetailCard 
          icon={<ImageIcon className="h-5 w-5 text-blue-500" />} 
          label="Frames Extracted" 
          value={scene.frame_count} 
          subValue="via ffmpeg"
        />
        <DetailCard 
          icon={<Box className="h-5 w-5 text-purple-500" />} 
          label="Input Type" 
          value={scene.input_type.toUpperCase()} 
          subValue={scene.input_path.split('/').pop() || ''}
        />
        <DetailCard 
          icon={<Database className="h-5 w-5 text-indigo-500" />} 
          label="VPS Index" 
          value={scene.faiss_index_path ? 'AVAILABLE' : 'PENDING'} 
          subValue={scene.faiss_index_path ? 'FAISS Index Built' : 'Not yet generated'}
        />
        <DetailCard 
          icon={<Activity className="h-5 w-5 text-green-500" />} 
          label="Splatting" 
          value={scene.splat_path ? 'READY' : 'PROCESSING'} 
          subValue={scene.splat_path ? '.ply exported' : 'Training in progress'}
        />
      </div>

      {scene.error_message && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 flex items-start space-x-4">
          <AlertCircle className="h-6 w-6 text-red-600 mt-1 flex-shrink-0" />
          <div>
            <h3 className="text-red-800 font-bold">Pipeline Error Detected</h3>
            <p className="text-red-700 mt-1 italic">"{scene.error_message}"</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-12">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
            <div className="p-4 border-b border-gray-100 bg-gray-50 flex items-center">
              <Info className="h-4 w-4 text-gray-500 mr-2" />
              <span className="font-bold text-gray-700 text-sm">System Paths</span>
            </div>
            <div className="p-6 space-y-4 font-mono text-xs">
              <PathRow label="Raw Input" path={scene.input_path} />
              <PathRow label="Frames Dir" path={scene.frames_dir} />
              <PathRow label="Sparse Model" path={scene.sparse_dir || 'N/A'} />
              <PathRow label="Splat Path" path={scene.splat_path || 'N/A'} />
              <PathRow label="FAISS Index" path={scene.faiss_index_path || 'N/A'} />
            </div>
          </div>
        </div>
        
        <div className="bg-indigo-600 rounded-2xl p-8 text-white shadow-xl shadow-indigo-200 flex flex-col justify-between">
          <div>
            <h3 className="text-2xl font-bold mb-4">Ready for Testing?</h3>
            <p className="text-indigo-100 mb-6">
              Once the pipeline reaches the "Ready" state, you can begin localization testing using query images from this environment.
            </p>
          </div>
          <button 
            disabled={scene.status !== 'READY'}
            className="w-full bg-white text-indigo-600 font-bold py-3 rounded-xl hover:bg-indigo-50 disabled:bg-indigo-400 disabled:text-indigo-200 transition-colors"
          >
            Go to Localization Test
          </button>
        </div>
      </div>
    </div>
  );
}

function DetailCard({ icon, label, value, subValue }: any) {
  return (
    <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center space-x-2 mb-4">
        {icon}
        <span className="text-xs font-bold text-gray-500 uppercase tracking-widest">{label}</span>
      </div>
      <div className="text-2xl font-extrabold text-gray-900">{value}</div>
      <div className="text-xs text-gray-400 mt-1 truncate">{subValue}</div>
    </div>
  );
}

function PathRow({ label, path }: any) {
  return (
    <div className="flex flex-col sm:flex-row sm:justify-between border-b border-gray-50 pb-2 last:border-0">
      <span className="text-gray-400 w-32 shrink-0">{label}:</span>
      <span className="text-gray-600 break-all">{path}</span>
    </div>
  );
}
