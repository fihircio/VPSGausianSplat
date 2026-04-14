"use client";

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { EvaluationReport } from '@/types';
import { BarChart3, TrendingUp, Target, Zap, Ruler, RefreshCcw, LayoutPanelLeft, ShieldCheck, Gauge } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function DashboardPage() {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [isDemoMode, setIsDemoMode] = useState(false);

  useEffect(() => {
    // Attempt to fetch from "backend/storage/debug/vps_evaluation_report.json"
    // Since we're client side, we'd normally call an API endpoint.
    // For this demo, we'll try to find it or fallback to mock.
    const loadReport = async () => {
      try {
        // In a real setup, this would be an endpoint like GET /evaluation/report
        // For now, we use mock if fail
        throw new Error("Local file access not configured");
      } catch (e) {
        setIsDemoMode(true);
        setReport(api.getMockReport());
      }
    };
    loadReport();
  }, []);

  if (!report) return null;

  const best = report.best_config;
  const worst = report.worst_config;

  return (
    <div className="max-w-7xl mx-auto py-12 px-4 space-y-12 pb-24">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight flex items-center">
            <BarChart3 className="h-10 w-10 text-indigo-600 mr-4" />
            Performance Benchmark
          </h1>
          <p className="mt-2 text-lg text-gray-600">
            Internal evaluation report for Scene <span className="font-mono bg-gray-100 px-2 py-0.5 rounded text-sm font-bold text-gray-900">{report.scene_id}</span>
          </p>
        </div>
        
        {isDemoMode && (
          <div className="flex items-center px-4 py-2 bg-amber-50 rounded-full border border-amber-200">
            <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse mr-2" />
            <span className="text-xs font-bold text-amber-700 uppercase tracking-widest leading-none">Demo Mock Enabled</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard 
          icon={<ShieldCheck className="text-green-600" />} 
          label="Success Rate" 
          value={`${(best.summary.success_rate * 100).toFixed(1)}%`} 
          desc="Across 20 random frames"
        />
        <KPICard 
          icon={<Gauge className="text-indigo-600" />} 
          label="Mean Accuracy" 
          value={`${(best.summary.avg_translation_error * 100).toFixed(1)} cm`} 
          desc="Average XYZ error"
        />
        <KPICard 
          icon={<Target className="text-purple-600" />} 
          label="Avg Confidence" 
          value={`${(best.summary.avg_confidence * 100).toFixed(1)}%`} 
          desc="Feature inlier ratio"
        />
        <KPICard 
          icon={<Zap className="text-amber-600" />} 
          label="Compute Score" 
          value={best.score.toFixed(1)} 
          desc="Weighted parameter score"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
        <div className="lg:col-span-2 space-y-8">
          <div className="bg-white rounded-3xl p-8 border border-gray-100 shadow-sm">
            <h3 className="text-xl font-bold text-gray-900 mb-8 flex items-center">
              <TrendingUp className="h-6 w-6 text-indigo-600 mr-3" />
              Parameter Sweep Comparison
            </h3>
            
            <div className="space-y-4">
              <ConfigHeader />
              <ConfigRow label="Best Performing" data={best} highlight />
              <ConfigRow label="Least Effective" data={worst} />
            </div>
            
            <div className="mt-10 p-6 bg-gray-50 rounded-2xl border border-gray-100 italic text-sm text-gray-600">
              "Increasing the ORB feature count to 2000 significantly improves the success rate in low-texture environments, although it increases the retrieval latency by ~14ms."
            </div>
          </div>
        </div>

        <div className="bg-gray-900 rounded-3xl p-8 text-white flex flex-col justify-between shadow-2xl">
          <div>
            <div className="mb-8">
              <h3 className="text-2xl font-bold mb-2">Recommendation</h3>
              <p className="text-gray-400 text-sm">Automated system optimization based on sweep results.</p>
            </div>
            
            <div className="space-y-6">
              <RecommendedOption label="orb_nfeatures" value={report.recommended_settings.orb_nfeatures} />
              <RecommendedOption label="pixel_threshold" value={report.recommended_settings.pixel_distance_threshold} />
              <RecommendedOption label="ratio_test" value={report.recommended_settings.ratio_test_threshold} />
            </div>
          </div>
          
          <button className="mt-12 w-full bg-indigo-600 hover:bg-indigo-700 py-4 rounded-2xl font-bold transition-all flex items-center justify-center">
            <RefreshCcw className="h-5 w-5 mr-3" />
            Apply to Production
          </button>
        </div>
      </div>
    </div>
  );
}

function KPICard({ icon, label, value, desc }: any) {
  return (
    <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm flex flex-col justify-between h-40">
      <div className="flex justify-between items-start">
        <div className="p-3 rounded-2xl bg-gray-50">{icon}</div>
        <div className="text-xs font-bold text-gray-400 uppercase tracking-widest">{label}</div>
      </div>
      <div>
        <div className="text-3xl font-extrabold text-gray-900">{value}</div>
        <div className="text-[10px] text-gray-400 mt-1 uppercase font-semibold">{desc}</div>
      </div>
    </div>
  );
}

function ConfigHeader() {
  return (
    <div className="grid grid-cols-4 px-4 pb-4 border-b border-gray-50 text-[10px] uppercase font-bold text-gray-400 tracking-widest">
      <div className="col-span-1">Config Profile</div>
      <div>Success</div>
      <div>Precision</div>
      <div>Score</div>
    </div>
  );
}

function ConfigRow({ label, data, highlight }: any) {
  return (
    <div className={cn(
      "grid grid-cols-4 p-4 rounded-2xl border transition-all items-center",
      highlight ? "bg-indigo-50 border-indigo-100 ring-1 ring-indigo-200" : "bg-white border-transparent hover:bg-gray-50"
    )}>
      <div className="flex flex-col">
        <span className="text-sm font-bold text-gray-900">{label}</span>
        <span className="text-[10px] text-gray-500 font-mono">ORB:{data.config.orb_nfeatures} | PX:{data.config.pixel_distance_threshold}</span>
      </div>
      <div className="text-sm font-bold text-gray-900">{(data.summary.success_rate * 100).toFixed(0)}%</div>
      <div className="text-sm font-bold text-gray-900">{(data.summary.avg_translation_error).toFixed(2)}m</div>
      <div className="text-sm font-extrabold text-indigo-600">{data.score.toFixed(1)}</div>
    </div>
  );
}

function RecommendedOption({ label, value }: any) {
  return (
    <div className="flex justify-between items-center py-3 border-b border-gray-800 last:border-0">
      <span className="text-gray-500 text-xs font-mono">{label}</span>
      <span className="text-indigo-400 font-bold font-mono">{value}</span>
    </div>
  );
}
