"use client";

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { Shield, Plus, Trash2, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function SettingsPage() {
  const [origins, setOrigins] = useState<string[]>([]);
  const [newOrigin, setNewOrigin] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadOrigins = async () => {
    setLoading(true);
    try {
      const resp = await api.getCorsOrigins();
      setOrigins(resp.origins);
    } catch {
      setError('Failed to load CORS origins.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadOrigins(); }, []);

  const handleAdd = async () => {
    const origin = newOrigin.trim();
    if (!origin) return;
    setError(null);
    setSuccessMsg(null);
    try {
      const resp = await api.addCorsOrigin(origin);
      setOrigins(resp.origins);
      setNewOrigin('');
      setSuccessMsg(`Added ${origin}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add origin.');
    }
  };

  const handleRemove = async (origin: string) => {
    setError(null);
    setSuccessMsg(null);
    try {
      const resp = await api.removeCorsOrigin(origin);
      setOrigins(resp.origins);
      setSuccessMsg(`Removed ${origin}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to remove origin.');
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-12 px-4">
      <div className="flex items-center space-x-4 mb-8">
        <div className="h-12 w-12 bg-indigo-100 rounded-2xl flex items-center justify-center">
          <Shield className="h-6 w-6 text-indigo-600" />
        </div>
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900">CORS Settings</h1>
          <p className="text-gray-500 mt-1">Manage allowed origins for cross-origin requests.</p>
        </div>
      </div>

      {error && (
        <div className="p-4 mb-6 bg-red-50 border border-red-100 rounded-2xl flex items-center gap-2 text-red-600 text-sm font-bold">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      {successMsg && (
        <div className="p-4 mb-6 bg-emerald-50 border border-emerald-100 rounded-2xl flex items-center gap-2 text-emerald-600 text-sm font-bold">
          <CheckCircle2 className="h-4 w-4" />
          {successMsg}
        </div>
      )}

      <div className="glass-card p-6 space-y-6">
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={newOrigin}
            onChange={(e) => setNewOrigin(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
            placeholder="https://example.com"
            className="flex-1 px-4 py-3 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none font-mono text-sm"
          />
          <button
            onClick={handleAdd}
            disabled={!newOrigin.trim()}
            className="px-5 py-3 bg-indigo-600 text-white rounded-xl font-bold text-sm hover:bg-indigo-700 disabled:opacity-50 transition flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Add
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        ) : origins.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <Shield className="h-10 w-10 mx-auto mb-3 opacity-40" />
            <p className="font-bold">No custom origins configured</p>
            <p className="text-sm mt-1">Add an origin above to restrict CORS access.</p>
            <p className="text-xs mt-3 text-gray-300">
              When no origins are configured, the backend falls back to the <code className="bg-gray-100 px-1 rounded">CORS_ALLOWED_ORIGINS</code> env var.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {origins.map((origin) => (
              <div
                key={origin}
                className="flex items-center justify-between px-4 py-3 bg-white border border-gray-100 rounded-xl hover:border-gray-200 transition"
              >
                <span className="font-mono text-sm text-gray-700">{origin}</span>
                <button
                  onClick={() => handleRemove(origin)}
                  className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
