"use client";

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Upload, FileVideo, X, CheckCircle2, Loader2, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [sceneName, setSceneName] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      if (selected.type.startsWith('video/') || selected.name.endsWith('.MOV')) {
        setFile(selected);
        setError(null);
        if (!sceneName) setSceneName(selected.name.split('.')[0]);
      } else {
        setError("Please select a valid video file (.mp4, .mov)");
      }
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    setError(null);
    setUploadProgress(10);

    try {
      // 1. Upload
      const scene = await api.uploadScene(file, sceneName);
      setUploadProgress(50);

      // 2. Trigger Process
      await api.processScene(scene.id);
      setUploadProgress(100);

      // 3. Redirect to monitoring
      setTimeout(() => {
        router.push(`/scenes/${scene.id}`);
      }, 1000);

    } catch (err: any) {
      setError(err.response?.data?.detail || "Upload failed. Please check backend connection.");
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const removeFile = () => {
    setFile(null);
    setUploadProgress(0);
  };

  return (
    <div className="vibrant-bg min-h-[calc(100vh-64px)] py-12 px-4 sm:px-6 lg:px-8 flex flex-col items-center">
      <div className="max-w-3xl w-full space-y-8">
        <div className="text-center">
          <motion.h1 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-4xl font-extrabold text-gray-900 tracking-tight"
          >
            Create New <span className="text-brand-primary">VPS Scene</span>
          </motion.h1>
          <p className="mt-2 text-gray-500 font-medium">
            Upload your hospital walkthrough to generate a high-precision 3D anchor.
          </p>
        </div>

        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="glass-card shadow-indigo-100/50"
        >
          {!file ? (
            <div 
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-indigo-200 rounded-2xl p-12 text-center cursor-pointer hover:border-indigo-400 hover:bg-indigo-50/50 transition-all group"
            >
              <input 
                type="file" 
                ref={fileInputRef} 
                onChange={handleFileChange} 
                className="hidden" 
                accept="video/*,.mov"
              />
              <div className="mx-auto h-16 w-16 bg-indigo-50 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform">
                <Upload className="h-8 w-8 text-indigo-500" />
              </div>
              <p className="mt-4 text-lg font-bold text-gray-900">Click to upload video</p>
              <p className="mt-1 text-sm text-gray-400 uppercase tracking-widest font-bold">MP4, MOV up to 500MB</p>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="flex items-center p-4 bg-indigo-50/50 rounded-2xl border border-indigo-100">
                <div className="h-12 w-12 bg-white rounded-xl flex items-center justify-center shadow-sm">
                  <FileVideo className="h-6 w-6 text-indigo-600" />
                </div>
                <div className="ml-4 flex-1 overflow-hidden">
                  <p className="text-sm font-bold text-gray-900 truncate">{file.name}</p>
                  <p className="text-xs text-gray-400 font-mono">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
                {!isUploading && (
                  <button onClick={removeFile} className="p-2 hover:bg-white rounded-full transition-colors">
                    <X className="h-5 w-5 text-gray-400" />
                  </button>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider ml-1">Scene Label</label>
                <input 
                  type="text" 
                  value={sceneName}
                  onChange={(e) => setSceneName(e.target.value)}
                  disabled={isUploading}
                  placeholder="e.g. Hospital Wing A - Level 2"
                  className="w-full px-4 py-3 bg-white/50 border border-gray-100 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all font-medium"
                />
              </div>

              <AnimatePresence>
                {error && (
                  <motion.div 
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="p-3 bg-red-50 text-red-600 rounded-xl text-xs font-bold flex items-center"
                  >
                    <AlertCircle className="h-4 w-4 mr-2" />
                    {error}
                  </motion.div>
                )}
              </AnimatePresence>

              <button 
                onClick={handleUpload}
                disabled={isUploading || !file}
                className={cn(
                  "w-full py-4 rounded-xl text-white font-bold text-lg transition-all flex items-center justify-center space-x-2",
                  isUploading 
                    ? "bg-indigo-300 cursor-not-allowed" 
                    : "bg-indigo-600 hover:bg-brand-primary shadow-xl shadow-indigo-100 hover:shadow-indigo-200 active:scale-[0.98]"
                )}
              >
                {isUploading ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Processing Ingestion {uploadProgress}%</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-5 w-5" />
                    <span>Initialize Map Generation</span>
                  </>
                )}
              </button>

              {isUploading && (
                <div className="w-full bg-gray-100 h-1.5 rounded-full overflow-hidden">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${uploadProgress}%` }}
                    className="h-full bg-indigo-600"
                  />
                </div>
              )}
            </div>
          )}
        </motion.div>

        <div className="grid grid-cols-3 gap-4">
          <InfoCard title="Step 1" desc="Video Upload" active={!file} />
          <InfoCard title="Step 2" desc="SfM Geometry" active={isUploading && uploadProgress < 60} />
          <InfoCard title="Step 3" desc="VPS Indexing" active={isUploading && uploadProgress >= 60} />
        </div>
      </div>
    </div>
  );
}

function InfoCard({ title, desc, active }: { title: string, desc: string, active: boolean }) {
  return (
    <div className={cn(
      "p-4 rounded-2xl border transition-all",
      active 
        ? "bg-white border-indigo-200 shadow-lg -translate-y-1" 
        : "bg-white/40 border-gray-100 grayscale-[0.5] opacity-60"
    )}>
      <div className="text-[10px] font-bold uppercase tracking-widest text-indigo-500 mb-1">{title}</div>
      <div className="text-sm font-extrabold text-gray-900">{desc}</div>
    </div>
  );
}
