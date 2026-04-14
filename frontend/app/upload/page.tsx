"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Upload, FileVideo, FileImage, Loader2 } from 'lucide-react';

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState('');

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setIsUploading(true);
    setError('');

    try {
      const scene = await api.uploadScene(file, name);
      await api.processScene(scene.id);
      router.push(`/scene/${scene.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-12 px-4">
      <div className="mb-10 text-center">
        <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight">Create New Scene</h1>
        <p className="mt-4 text-lg text-gray-600">
          Upload a video or image capture to generate a Gaussian Splatting environment and VPS index.
        </p>
      </div>

      <form onSubmit={handleUpload} className="space-y-8 bg-white p-8 rounded-2xl shadow-xl shadow-indigo-100/50 border border-gray-100">
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">Scene Name (Optional)</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Retail Store - Level 1"
            className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all outline-none"
          />
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-semibold text-gray-700">Capture File</label>
          <div className="relative group">
            <input
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
              accept="video/*,image/*"
            />
            <div className="border-2 border-dashed border-gray-300 rounded-xl p-10 flex flex-col items-center justify-center transition-all group-hover:border-indigo-400 group-hover:bg-indigo-50/10">
              {file ? (
                <div className="flex items-center space-x-3 text-indigo-600">
                  {file.type.startsWith('video') ? <FileVideo className="h-10 w-10" /> : <FileImage className="h-10 w-10" />}
                  <span className="text-lg font-medium">{file.name}</span>
                </div>
              ) : (
                <>
                  <Upload className="h-12 w-12 text-gray-400 group-hover:text-indigo-500 mb-4 transition-colors" />
                  <p className="text-gray-600 font-medium">Click or drag capture file (MP4, MOV, JPG, PNG)</p>
                  <p className="text-sm text-gray-400 mt-2">Maximum file size: 500MB</p>
                </>
              )}
            </div>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-50 text-red-700 rounded-lg text-sm font-medium border border-red-100">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={!file || isUploading}
          className="w-full bg-indigo-600 text-white py-4 rounded-xl font-bold text-lg hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-all flex items-center justify-center shadow-lg shadow-indigo-200"
        >
          {isUploading ? (
            <>
              <Loader2 className="h-5 w-5 mr-3 animate-spin" />
              Processing Initial Upload...
            </>
          ) : (
            'Start Pipeline'
          )}
        </button>
      </form>
    </div>
  );
}
