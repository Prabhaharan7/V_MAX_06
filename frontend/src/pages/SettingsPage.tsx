import React from "react";
import { Sliders, Database, Cpu } from "lucide-react";

export const SettingsPage: React.FC = () => {

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="border-b border-slate-800/80 pb-2">
        <div className="flex items-center space-x-2">
          <h1 className="text-2xl font-black tracking-tight text-white">
            System & NLP Model Configuration
          </h1>
          <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded">
            ADMIN / HSE SETTINGS
          </span>
        </div>
        <p className="text-xs text-slate-400 font-normal mt-0.5">
          Calibrate SIF classification thresholds, rolling window durations, and vector embeddings
        </p>
      </div>

      <div className="space-y-4">
        {/* Card 1: Classifier Cutoffs */}
        <div className="p-6 rounded-xl bg-[#0c1322]/90 border border-slate-800/90 shadow-xl backdrop-blur-md space-y-4">
          <div className="flex items-center space-x-2 text-white font-mono font-bold text-sm">
            <Sliders className="w-4 h-4 text-amber-400" />
            <span>SIF-Potential Classification Thresholds</span>
          </div>

          <div className="grid sm:grid-cols-2 gap-4 text-xs font-mono">
            <div className="space-y-1.5">
              <label className="text-slate-400">Auto-Confirm SIF Threshold (Default: 0.60)</label>
              <input
                type="number"
                step="0.05"
                defaultValue={0.60}
                className="w-full px-3 py-2 bg-slate-950/70 border border-slate-800 rounded-lg text-white"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-slate-400">Review Queue Lower Bound (Default: 0.40)</label>
              <input
                type="number"
                step="0.05"
                defaultValue={0.40}
                className="w-full px-3 py-2 bg-slate-950/70 border border-slate-800 rounded-lg text-white"
              />
            </div>
          </div>
        </div>

        {/* Card 2: Aggregation Service Windows */}
        <div className="p-6 rounded-xl bg-[#0c1322]/90 border border-slate-800/90 shadow-xl backdrop-blur-md space-y-4">
          <div className="flex items-center space-x-2 text-white font-mono font-bold text-sm">
            <Database className="w-4 h-4 text-cyan-400" />
            <span>Rolling Pattern Mining Service Parameters</span>
          </div>

          <div className="grid sm:grid-cols-2 gap-4 text-xs font-mono">
            <div className="space-y-1.5">
              <label className="text-slate-400">Rolling Recent Window (Days)</label>
              <input
                type="number"
                defaultValue={90}
                className="w-full px-3 py-2 bg-slate-950/70 border border-slate-800 rounded-lg text-white"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-slate-400">Comparison Baseline Window (Days)</label>
              <input
                type="number"
                defaultValue={90}
                className="w-full px-3 py-2 bg-slate-950/70 border border-slate-800 rounded-lg text-white"
              />
            </div>
          </div>
        </div>

        {/* Card 3: Model & Vector Engine */}
        <div className="p-6 rounded-xl bg-[#0c1322]/90 border border-slate-800/90 shadow-xl backdrop-blur-md space-y-3">
          <div className="flex items-center space-x-2 text-white font-mono font-bold text-sm">
            <Cpu className="w-4 h-4 text-emerald-400" />
            <span>Semantic Vector Engine & Safety Memory</span>
          </div>

          <div className="text-xs font-mono space-y-2 text-slate-300">
            <div className="flex justify-between border-b border-slate-800/80 pb-2">
              <span className="text-slate-400">Embeddings Engine:</span>
              <span className="text-emerald-400">sentence-transformers (all-MiniLM-L6-v2)</span>
            </div>
            <div className="flex justify-between border-b border-slate-800/80 pb-2">
              <span className="text-slate-400">Vector Dimension:</span>
              <span className="text-slate-100">384 Dimensions</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Database Engine:</span>
              <span className="text-slate-100">PostgreSQL 16 + pgvector</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
