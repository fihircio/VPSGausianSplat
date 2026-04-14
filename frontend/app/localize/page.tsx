"use client";

import { useState } from 'react';
import { api } from '@/lib/api';
import { LocalizeResponse } from '@/types';
import { Search, Upload, Loader2, MapPin, Compass, Percent, CheckCircle, Crosshair } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function LocalizePage() {
  const [sceneId, setSceneId] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [isLocalizing, setIsLocalizing] = useState(false);
  const [result, setResult] = useState<LocalizeResponse | null>(null);
  const [error, setError] = useState('');

  const handleLocalize = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !sceneId) return;

    setIsLocalizing(true);
    setError('');
    setResult(null);

    try {
      const data = await api.localize(sceneId, file);
      setResult(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Localization failed. Ensure the scene is READY and the query image is compatible.');
    } finally {
      setIsLocalizing(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-12 px-4">
      <div className="mb-12 text-center">
        <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight">VPS Localization Test</h1>
        <p className="mt-4 text-lg text-gray-600">
          Verify 6DoF pose estimation accuracy by uploading a query image against a processed scene.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-12">
        <div className="lg:col-span-2 space-y-8">
          <form onSubmit={handleLocalize} className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 space-y-6">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Target Scene ID</label>
              <div className="relative">
                <Search className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  value={sceneId}
                  onChange={(e) => setSceneId(e.target.value)}
                  placeholder="Paste UUID here..."
                  className="w-full pl-10 pr-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 transition-all outline-none font-mono text-sm"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Query Image</label>
              <div className="relative group">
                <input
                  type="file"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                  accept="image/*"
                  required
                />
                <div className="border-2 border-dashed border-gray-200 rounded-xl p-6 flex flex-col items-center justify-center transition-all group-hover:border-indigo-400 group-hover:bg-indigo-50/10">
                  {file ? (
                    <span className="text-indigo-600 font-medium truncate max-w-full">{file.name}</span>
                  ) : (
                    <>
                      <Upload className="h-8 w-8 text-gray-400 mb-2" />
                      <span className="text-sm text-gray-500">Pick query image</span>
                    </>
                  )}
                </div>
              </div>
            </div>

            {error && (
              <div className="p-3 bg-red-50 text-red-700 rounded-lg text-xs font-medium border border-red-100">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={!file || !sceneId || isLocalizing}
              className="w-full bg-indigo-600 text-white py-3 rounded-xl font-bold hover:bg-indigo-700 disabled:bg-gray-300 transition-all flex items-center justify-center"
            >
              {isLocalizing ? (
                <>
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  Localizing...
                </>
              ) : (
                'Run Evaluation'
              )}
            </button>
          </form>
          
          <div className="bg-indigo-50 rounded-xl p-6 border border-indigo-100">
            <h4 className="text-indigo-900 font-bold text-sm flex items-center mb-2">
              <CheckCircle className="h-4 w-4 mr-2" />
              Pro Tip for Demo
            </h4>
            <p className="text-indigo-700 text-sm leading-relaxed">
              Use a query image taken at a different angle but within the same physical room for the best visual pose result.
            </p>
          </div>
        </div>

        <div className="lg:col-span-3">
          {result ? (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="bg-white p-8 rounded-2xl shadow-xl shadow-indigo-100 border border-gray-100">
                <div className="flex items-center justify-between mb-8">
                  <h2 className="text-2xl font-bold flex items-center">
                    <Crosshair className="h-6 w-6 text-indigo-600 mr-3" />
                    Estimation Result
                  </h2>
                  <div className={cn(
                    "px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-tighter",
                    result.confidence > 0.7 ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
                  )}>
                    {result.confidence > 0.7 ? 'High Accuracy' : 'Low Confidence'}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <PoseMetric 
                    icon={<MapPin className="h-5 w-5" />} 
                    label="World Position [X, Y, Z]" 
                    value={result.position.map(v => v.toFixed(3)).join(', ')} 
                    color="text-blue-600"
                  />
                  <PoseMetric 
                    icon={<Compass className="h-5 w-5" />} 
                    label="Rotation Quaternion [X, Y, Z, W]" 
                    value={result.rotation.map(v => v.toFixed(4)).join(', ')} 
                    color="text-purple-600"
                  />
                  <PoseMetric 
                    icon={<Percent className="h-5 w-5" />} 
                    label="Confidence Score" 
                    value={`${(result.confidence * 100).toFixed(1)}%`} 
                    color="text-green-600"
                  />
                  <PoseMetric 
                    icon={<Search className="h-5 w-5" />} 
                    label="Feature Inliers" 
                    value={`${result.inliers} points`} 
                    color="text-amber-600"
                  />
                </div>
              </div>
              
              <div className="bg-gray-900 rounded-2xl p-6 text-white font-mono text-[10px] leading-tight overflow-x-auto shadow-2xl">
                <div className="text-gray-500 mb-2 uppercase tracking-widest text-[8px] font-bold">Raw JSON Payload</div>
                <pre>{JSON.stringify(result, null, 2)}</pre>
              </div>
            </div>
          ) : (
            <div className="h-full min-h-[400px] border-2 border-dashed border-gray-200 rounded-2xl flex flex-col items-center justify-center text-gray-400 p-12 text-center">
              <Crosshair className="h-16 w-16 mb-4 opacity-20" />
              <p className="max-w-xs">Results will appear here once the localization engine completes the pose estimation.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function PoseMetric({ icon, label, value, color }: any) {
  return (
    <div className="space-y-2">
      <div className="flex items-center text-gray-500 text-xs font-bold uppercase tracking-widest">
        <span className={cn("mr-2 p-1.5 rounded-lg bg-gray-50", color)}>{icon}</span>
        {label}
      </div>
      <div className="text-lg font-mono font-bold text-gray-900 pl-11">{value}</div>
    </div>
  );
}
