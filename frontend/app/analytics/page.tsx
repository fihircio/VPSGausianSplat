"use client";

import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { api } from '@/lib/api';
import { AnalyticsOverview, SceneAnalytics, DailyQueryCount } from '@/types';
import { BarChart3, Activity, Target, Gauge, Loader2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function AnalyticsPage() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [daily, setDaily] = useState<DailyQueryCount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [ov, da] = await Promise.all([
          api.getAnalyticsOverview(),
          api.getDailyAnalytics(14),
        ]);
        setOverview(ov);
        setDaily(da.daily);
      } catch {
        setError('Failed to load analytics data. Is Redis running?');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto py-12 px-4">
        <div className="p-6 bg-amber-50 border border-amber-200 rounded-3xl flex items-center gap-4">
          <AlertCircle className="h-6 w-6 text-amber-600" />
          <div>
            <p className="font-bold text-amber-800">{error}</p>
            <p className="text-sm text-amber-600 mt-1">Start a VPS query first to populate metrics.</p>
          </div>
        </div>
      </div>
    );
  }

  const scenes = overview?.scenes || [];

  return (
    <div className="max-w-7xl mx-auto py-12 px-4 space-y-10">
      <div className="flex items-center space-x-4">
        <div className="h-12 w-12 bg-indigo-100 rounded-2xl flex items-center justify-center">
          <BarChart3 className="h-6 w-6 text-indigo-600" />
        </div>
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900">Analytics</h1>
          <p className="text-gray-500 mt-1">VPS query metrics and performance.</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <SummaryCard icon={<Activity />} label="Total Queries" value={overview?.total_queries ?? 0} color="text-indigo-600" bg="bg-indigo-50" />
        <SummaryCard icon={<Target />} label="Scenes Tracked" value={scenes.length} color="text-emerald-600" bg="bg-emerald-50" />
        <SummaryCard icon={<Gauge />} label="Avg Success Rate" value={scenes.length > 0 ? `${(scenes.reduce((s, c) => s + c.success_rate, 0) / scenes.length * 100).toFixed(0)}%` : '---'} color="text-amber-600" bg="bg-amber-50" />
      </div>

      {/* Daily Queries Chart */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-6">Queries per Day</h2>
        {daily.length === 0 || daily.every(d => d.queries === 0) ? (
          <div className="text-center py-12 text-gray-400">
            <BarChart3 className="h-10 w-10 mx-auto mb-3 opacity-40" />
            <p className="font-bold">No daily data yet</p>
            <p className="text-sm">Queries will appear here once Redis metrics are populated.</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={daily}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="queries" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Per-Scene Stats */}
      {scenes.length > 0 && (
        <div className="space-y-6">
          <h2 className="text-lg font-bold text-gray-900">Per-Scene Breakdown</h2>
          {scenes.map((scene) => (
            <SceneCard key={scene.scene_id} scene={scene} />
          ))}
        </div>
      )}
    </div>
  );
}

function SummaryCard({ icon, label, value, color, bg }: { icon: React.ReactNode; label: string; value: string | number; color: string; bg: string }) {
  return (
    <div className="glass-card p-6 flex items-center gap-4">
      <div className={cn("p-3 rounded-xl", bg)}>
        <div className={cn("h-5 w-5", color)}>{icon}</div>
      </div>
      <div>
        <p className="text-2xl font-black text-gray-900">{value}</p>
        <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">{label}</p>
      </div>
    </div>
  );
}

function SceneCard({ scene }: { scene: SceneAnalytics }) {
  const latency = scene.latency_ms;

  return (
    <div className="glass-card p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-bold text-gray-900 font-mono text-sm">{scene.scene_id}</p>
          <p className="text-xs text-gray-500 mt-0.5">
            {scene.total_queries} queries · {(scene.success_rate * 100).toFixed(0)}% success
          </p>
        </div>
        <div className={cn(
          "px-3 py-1 rounded-full text-xs font-bold",
          scene.success_rate >= 0.8 ? "bg-emerald-50 text-emerald-700" :
          scene.success_rate >= 0.5 ? "bg-amber-50 text-amber-700" :
          "bg-red-50 text-red-700"
        )}>
          {scene.success_count} / {scene.total_queries} OK
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        <Metric label="P50" value={latency ? `${latency.p50.toFixed(0)}ms` : '---'} />
        <Metric label="P95" value={latency ? `${latency.p95.toFixed(0)}ms` : '---'} />
        <Metric label="P99" value={latency ? `${latency.p99.toFixed(0)}ms` : '---'} />
        <Metric label="Min" value={latency ? `${latency.min.toFixed(0)}ms` : '---'} />
        <Metric label="Max" value={latency ? `${latency.max.toFixed(0)}ms` : '---'} />
      </div>

      {latency && (
        <div className="h-1 w-full bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-emerald-400 via-amber-400 to-red-400 rounded-full"
            style={{ width: `${Math.min(latency.p99 / 10, 100)}%` }}
          />
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white border border-gray-100 rounded-xl p-3 text-center">
      <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">{label}</p>
      <p className="text-lg font-black text-gray-900 mt-0.5">{value}</p>
    </div>
  );
}
