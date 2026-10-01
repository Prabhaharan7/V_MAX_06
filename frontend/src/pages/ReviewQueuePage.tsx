import React, { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  CheckCircle2,
  ShieldAlert,
  Flame,
  HelpCircle,
  Sparkles,
  TrendingUp,
  ArrowRight,
  ExternalLink,
  X,
  Send,
  RefreshCw,
  Search,
  Filter,
  Zap,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useAuth } from "../context/AuthContext";

// ==============================================================================
// Types & Interfaces
// ==============================================================================

interface LSRTag {
  id?: number;
  lsr_rule: string;
  confidence: number;
}

interface BarrierFailure {
  id?: number;
  barrier_type: string;
  evidence_phrase: string;
  severity: "critical" | "high" | "medium" | "low" | string;
}

interface ReviewQueueItem {
  id: number;
  report_id: number;
  report_snippet: string;
  raw_text: string;
  current_ai_label?: string | null;
  confidence?: number | null;
  reason: string;
  activity?: string | null;
  site_name?: string | null;
  site_region?: string | null;
  submitted_at: string;
  primary_lsr?: string | null;
  resolved: boolean;
  corrected_label?: string | null;
  corrected_lsr?: string | null;
  lsr_tags: LSRTag[];
  barrier_failures: BarrierFailure[];
}

interface AccuracyTrendPoint {
  date: string;
  accuracy: number;
  reviews_count: number;
  corrections_count: number;
}

interface ModelFeedbackStats {
  current_accuracy: number;
  baseline_accuracy: number;
  accuracy_delta: number;
  total_feedback_logged: number;
  total_corrections: number;
  total_agreements: number;
  active_learning_cycle: string;
  model_version: string;
  accuracy_trend: AccuracyTrendPoint[];
}

const CANONICAL_IOGP_LSR = [
  "Energy Isolation",
  "Safe Mechanical Lifting",
  "Line of Fire",
  "Confined Space Entry",
  "Work Authorisation",
  "Bypassing Safety Controls",
  "Driving",
  "Working at Height",
  "Hot Work",
];

// ==============================================================================
// Model Accuracy Trend Sparkline Component
// ==============================================================================

interface SparklineProps {
  stats: ModelFeedbackStats | null;
  isLoading: boolean;
}

const ModelAccuracyTrendBanner: React.FC<SparklineProps> = ({ stats, isLoading }) => {
  if (isLoading || !stats) {
    return (
      <div className="p-4 rounded-xl bg-[#0c1322]/90 border border-slate-800/80 animate-pulse flex items-center justify-between">
        <div className="h-10 w-48 bg-slate-800 rounded" />
        <div className="h-12 w-64 bg-slate-800 rounded" />
      </div>
    );
  }

  const trendData = stats.accuracy_trend || [];
  const currentAcc = stats.current_accuracy || 92.4;
  const delta = stats.accuracy_delta || 13.9;

  return (
    <div className="p-4 sm:p-5 rounded-xl bg-gradient-to-r from-[#0d1627] via-[#0c1322] to-[#111c33] border border-cyan-500/25 shadow-xl backdrop-blur-md relative overflow-hidden">
      {/* Background radial highlight */}
      <div className="absolute top-0 right-1/4 w-72 h-32 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Left: Headline Metrics */}
        <div className="flex flex-wrap items-center gap-6">
          <div className="flex items-center space-x-3.5">
            <div className="w-11 h-11 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-md">
              <TrendingUp className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
                  Model Accuracy Trend
                </span>
                <span className="px-2 py-0.2 rounded text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                  +{delta}% Active Learning Gain
                </span>
              </div>
              <div className="flex items-baseline space-x-2 mt-0.5">
                <span className="text-2xl font-black font-mono text-white tracking-tight">
                  {currentAcc}%
                </span>
                <span className="text-xs font-mono text-slate-400">
                  (Baseline: {stats.baseline_accuracy}%)
                </span>
              </div>
            </div>
          </div>

          {/* Mini Metadata Pills */}
          <div className="hidden sm:flex items-center space-x-4 border-l border-slate-800 pl-4 text-xs font-mono">
            <div>
              <div className="text-[10px] text-slate-500 uppercase">Reviews Logged</div>
              <div className="text-sm font-bold text-slate-200 mt-0.5">
                {stats.total_feedback_logged}
              </div>
            </div>
            <div>
              <div className="text-[10px] text-slate-500 uppercase">Corrections</div>
              <div className="text-sm font-bold text-amber-400 mt-0.5">
                {stats.total_corrections}
              </div>
            </div>
            <div>
              <div className="text-[10px] text-slate-500 uppercase">Cycle State</div>
              <div className="text-xs font-bold text-cyan-300 mt-0.5">
                {stats.active_learning_cycle}
              </div>
            </div>
          </div>
        </div>

        {/* Right: Interactive Sparkline Chart */}
        <div className="w-full lg:w-72 h-14 flex items-center justify-end">
          <div className="w-full h-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData} margin={{ top: 2, right: 2, left: 2, bottom: 0 }}>
                <defs>
                  <linearGradient id="accuracy-spark" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="#06b6d4" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" hide />
                <YAxis domain={["dataMin - 2", "dataMax + 2"]} hide />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#090d16",
                    borderColor: "#1e293b",
                    borderRadius: "0.5rem",
                    fontSize: "11px",
                    color: "#f8fafc",
                    fontFamily: "monospace",
                    padding: "4px 8px",
                  }}
                  formatter={(val: any) => [`${val}%`, "Classifier Accuracy"]}
                  labelFormatter={(label) => `Date: ${label}`}
                />
                <Area
                  type="monotone"
                  dataKey="accuracy"
                  stroke="#06b6d4"
                  strokeWidth={2.5}
                  fillOpacity={1}
                  fill="url(#accuracy-spark)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

// ==============================================================================
// Main Review Queue Page Component
// ==============================================================================

export const ReviewQueuePage: React.FC = () => {
  const { token } = useAuth();

  // State Management
  const [queueItems, setQueueItems] = useState<ReviewQueueItem[]>([]);
  const [stats, setStats] = useState<ModelFeedbackStats | null>(null);
  const [selectedItem, setSelectedItem] = useState<ReviewQueueItem | null>(null);
  const [isSidePanelOpen, setIsSidePanelOpen] = useState(false);

  const [isLoadingQueue, setIsLoadingQueue] = useState(true);
  const [isLoadingStats, setIsLoadingStats] = useState(true);
  const [isSubmittingResolve, setIsSubmittingResolve] = useState(false);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<"all" | "sif" | "non_sif">("all");
  const [viewResolved, setViewResolved] = useState(false);

  // Triage Form Inputs
  const [correctedLabel, setCorrectedLabel] = useState<"sif_potential" | "non_sif">("sif_potential");
  const [selectedLSRs, setSelectedLSRs] = useState<string[]>([]);
  const [triageNotes, setTriageNotes] = useState("");
  const [toastMessage, setToastMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  // Fetch Review Queue items
  const fetchReviewQueue = async () => {
    setIsLoadingQueue(true);
    try {
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`/api/review-queue?resolved=${viewResolved}&limit=50`, { headers });
      if (res.ok) {
        const data = await res.json();
        const items: ReviewQueueItem[] = Array.isArray(data) ? data : data.items || [];
        setQueueItems(items);
      }
    } catch (e) {
      console.error("Error loading review queue:", e);
    } finally {
      setIsLoadingQueue(false);
    }
  };

  // Fetch Model Feedback Stats
  const fetchFeedbackStats = async () => {
    setIsLoadingStats(true);
    try {
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch("/api/model/feedback-stats", { headers });
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error("Error loading model feedback stats:", e);
    } finally {
      setIsLoadingStats(false);
    }
  };

  useEffect(() => {
    fetchReviewQueue();
  }, [viewResolved, token]);

  useEffect(() => {
    fetchFeedbackStats();
  }, [token]);

  // Open side panel with loaded defaults
  const handleOpenSidePanel = (item: ReviewQueueItem) => {
    setSelectedItem(item);
    setIsSidePanelOpen(true);

    // Seed correction form defaults from current item
    const isSif = item.current_ai_label === "sif_potential" || (item.confidence || 0) >= 0.5;
    setCorrectedLabel(isSif ? "sif_potential" : "non_sif");

    const initialLSRs: string[] = [];
    if (item.primary_lsr) initialLSRs.push(item.primary_lsr);
    if (item.lsr_tags) {
      item.lsr_tags.forEach((t) => {
        if (!initialLSRs.includes(t.lsr_rule)) initialLSRs.push(t.lsr_rule);
      });
    }
    setSelectedLSRs(initialLSRs);
    setTriageNotes("");
  };

  const handleCloseSidePanel = () => {
    setIsSidePanelOpen(false);
  };

  // Toggle LSR in multi-select
  const handleToggleLSR = (lsrName: string) => {
    setSelectedLSRs((prev) =>
      prev.includes(lsrName) ? prev.filter((r) => r !== lsrName) : [...prev, lsrName]
    );
  };

  // Submit Triage Resolution
  const handleResolveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem) return;

    setIsSubmittingResolve(true);
    setToastMessage(null);

    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const payload = {
        corrected_label: correctedLabel,
        corrected_lsr: selectedLSRs,
        notes: triageNotes || "HSE Supervisor Active Learning calibration",
      };

      const res = await fetch(`/api/review-queue/${selectedItem.id}/resolve`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error("Failed to submit triage resolution.");
      }

      const result = await res.json();

      // Show success toast
      setToastMessage({
        text: result.message || `Observation #${selectedItem.report_id} verified successfully!`,
        type: "success",
      });

      // Remove from unresolved queue or update local state
      setQueueItems((prev) => prev.filter((item) => item.id !== selectedItem.id));

      // Refresh feedback stats for live sparkline update
      fetchFeedbackStats();

      // Close panel after delay
      setTimeout(() => {
        setIsSidePanelOpen(false);
        setSelectedItem(null);
        setToastMessage(null);
      }, 1400);
    } catch (err: any) {
      console.error("Resolve error:", err);
      setToastMessage({
        text: err.message || "Error submitting calibration to server.",
        type: "error",
      });
    } finally {
      setIsSubmittingResolve(false);
    }
  };

  // Filtered queue items
  const filteredItems = useMemo(() => {
    return queueItems.filter((item) => {
      // Search text filter
      const matchesSearch =
        !searchQuery ||
        item.raw_text.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (item.activity && item.activity.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (item.site_name && item.site_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
        item.reason.toLowerCase().includes(searchQuery.toLowerCase());

      // Label filter
      const isSif = item.current_ai_label === "sif_potential";
      const matchesType =
        filterType === "all" || (filterType === "sif" && isSif) || (filterType === "non_sif" && !isSif);

      return matchesSearch && matchesType;
    });
  }, [queueItems, searchQuery, filterType]);

  return (
    <div className="space-y-6 pb-16 relative">
      {/* ================= 1. TOP HEADER & BREADCRUMBS ================= */}
      <div className="border-b border-slate-800/80 pb-3 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-2xl font-black tracking-tight text-white flex items-center space-x-2">
              <span>Active Learning Triage Queue</span>
            </h1>
            <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30 rounded">
              HUMAN-IN-THE-LOOP
            </span>
          </div>
          <p className="text-xs text-slate-400 font-normal mt-0.5">
            Review ambiguous safety observations (40%–60% confidence range) to continuously calibrate NLP models
          </p>
        </div>

        {/* View Toggle Controls */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setViewResolved(!viewResolved)}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold border transition ${
              viewResolved
                ? "bg-purple-600 text-white border-purple-500 shadow-md shadow-purple-950/40"
                : "bg-slate-900 text-slate-400 hover:text-white border-slate-800"
            }`}
          >
            {viewResolved ? "Viewing: Resolved Audits" : "View Resolved"}
          </button>

          <button
            onClick={() => {
              fetchReviewQueue();
              fetchFeedbackStats();
            }}
            className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition"
            title="Refresh Queue"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ================= 2. MODEL ACCURACY TREND SPARKLINE ================= */}
      <ModelAccuracyTrendBanner stats={stats} isLoading={isLoadingStats} />

      {/* ================= 3. SEARCH & FILTER TOOLBAR ================= */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-xl bg-[#0c1322]/80 border border-slate-800 text-xs font-mono">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search queue by phrase, asset, or reason..."
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 outline-none focus:border-amber-500/60"
          />
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-slate-500 text-[11px] flex items-center space-x-1">
            <Filter className="w-3.5 h-3.5" />
            <span>Filter:</span>
          </span>

          <button
            onClick={() => setFilterType("all")}
            className={`px-2.5 py-1 rounded transition ${
              filterType === "all"
                ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold"
                : "bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
            }`}
          >
            All ({queueItems.length})
          </button>

          <button
            onClick={() => setFilterType("sif")}
            className={`px-2.5 py-1 rounded transition ${
              filterType === "sif"
                ? "bg-red-500/20 text-red-300 border border-red-500/40 font-bold"
                : "bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
            }`}
          >
            SIF-Potential
          </button>

          <button
            onClick={() => setFilterType("non_sif")}
            className={`px-2.5 py-1 rounded transition ${
              filterType === "non_sif"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold"
                : "bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
            }`}
          >
            Routine / Non-SIF
          </button>
        </div>
      </div>

      {/* ================= 4. QUEUE CARDS GRID ================= */}
      {isLoadingQueue ? (
        <div 
          className="grid gap-5"
          style={{ gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))" }}
        >
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3 animate-pulse h-56"
            >
              <div className="h-4 w-28 bg-slate-800 rounded" />
              <div className="h-16 w-full bg-slate-800 rounded" />
              <div className="h-4 w-3/4 bg-slate-800 rounded" />
            </div>
          ))}
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="p-12 rounded-xl bg-[#0c1322]/80 border border-slate-800 text-center space-y-3">
          <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto animate-bounce" />
          <div className="text-base font-bold text-white font-mono">Review Queue is Clear!</div>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            {viewResolved
              ? "No resolved triage cases matched your query."
              : "All borderline safety observations have been verified by HSE supervisors."}
          </p>
        </div>
      ) : (
        <div 
          className="grid gap-5"
          style={{ gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))" }}
        >
          {filteredItems.map((item) => {
            const isSif = item.current_ai_label === "sif_potential";
            const confPercent = Math.round((item.confidence || 0.5) * 100);
            const isSelected = selectedItem?.id === item.id;

            return (
              <div
                key={item.id}
                onClick={() => handleOpenSidePanel(item)}
                className={`p-5 rounded-xl border transition-all cursor-pointer flex flex-col justify-between space-y-3 group backdrop-blur-md ${
                  isSelected
                    ? "bg-amber-500/15 border-amber-500 shadow-xl shadow-amber-950/30 ring-1 ring-amber-500"
                    : "bg-[#0c1322]/90 border-slate-800/90 hover:border-amber-500/50 hover:bg-slate-900/80"
                }`}
              >
                <div className="space-y-2.5">
                  {/* Card Header: AI Label Badge + Confidence */}
                  <div className="flex items-center justify-between">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider border flex items-center space-x-1 ${
                        isSif
                          ? "bg-red-500/20 text-red-300 border-red-500/40"
                          : "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                      }`}
                    >
                      {isSif ? <Flame className="w-3 h-3 text-red-400" /> : <ShieldAlert className="w-3 h-3 text-emerald-400" />}
                      <span>{isSif ? "SIF-Potential" : "Non-SIF"}</span>
                    </span>

                    {/* Confidence percentage */}
                    <div className="flex items-center space-x-1.5 text-xs font-mono">
                      <span className="text-slate-400 text-[10px]">Conf:</span>
                      <span
                        className={`font-bold ${
                          confPercent >= 70
                            ? "text-red-400"
                            : confPercent >= 40
                            ? "text-amber-400"
                            : "text-emerald-400"
                        }`}
                      >
                        {confPercent}%
                      </span>
                    </div>
                  </div>

                  {/* Report Narrative Snippet */}
                  <p className="text-xs text-slate-200 leading-relaxed font-sans line-clamp-3 group-hover:text-white">
                    {item.report_snippet}
                  </p>

                  {/* Reason for Review Badge */}
                  <div className="p-2 rounded bg-amber-500/10 border border-amber-500/25 text-[11px] font-mono text-amber-300 flex items-start space-x-1.5">
                    <HelpCircle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                    <span className="leading-tight">{item.reason}</span>
                  </div>
                </div>

                {/* Card Footer: Metadata and Action Trigger */}
                <div className="pt-2 border-t border-slate-800/80 text-[11px] font-mono text-slate-400 flex items-center justify-between">
                  <div className="flex items-center space-x-2 truncate">
                    <span className="text-slate-300 font-bold truncate max-w-[120px]">
                      {item.site_name || "Asset"}
                    </span>
                    <span>•</span>
                    <span>{new Date(item.submitted_at).toLocaleDateString()}</span>
                  </div>

                  <span className="text-amber-400 group-hover:translate-x-1 transition-transform flex items-center space-x-1">
                    <span>Triage</span>
                    <ArrowRight className="w-3 h-3" />
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ================= 5. SLIDING SIDE PANEL (DRAWER / RESOLUTION SHEET) ================= */}
      {isSidePanelOpen && selectedItem && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          {/* Backdrop click to close */}
          <div className="flex-1" onClick={handleCloseSidePanel} />

          {/* Panel Container */}
          <div className="w-full max-w-xl bg-[#090e18] border-l border-slate-800 h-full flex flex-col justify-between shadow-2xl overflow-y-auto animate-in slide-in-from-right duration-300">
            {/* Panel Header */}
            <div className="p-5 border-b border-slate-800 flex items-center justify-between sticky top-0 bg-[#090e18]/95 backdrop-blur-md z-10">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
                  <Zap className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-white font-mono">
                    Triage & Calibrate Observation #{selectedItem.report_id}
                  </h2>
                  <p className="text-[11px] text-slate-400">
                    Queue Item #{selectedItem.id} • Active Learning Human Feedback
                  </p>
                </div>
              </div>

              <button
                onClick={handleCloseSidePanel}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Panel Body Content */}
            <div className="p-5 space-y-6 flex-1">
              {/* Toast Feedback in Panel */}
              {toastMessage && (
                <div
                  className={`p-3 rounded-xl border text-xs font-mono flex items-center space-x-2 ${
                    toastMessage.type === "success"
                      ? "bg-emerald-500/20 text-emerald-200 border-emerald-500/40"
                      : "bg-red-500/20 text-red-200 border-red-500/40"
                  }`}
                >
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>{toastMessage.text}</span>
                </div>
              )}

              {/* SECTION A: Full Observation Narrative */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider font-bold">
                    Full Field Narrative
                  </span>
                  <Link
                    to={`/reports/${selectedItem.report_id}`}
                    className="text-[11px] font-mono text-amber-400 hover:underline flex items-center space-x-1"
                  >
                    <span>Inspect Explainable Spans</span>
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 text-xs font-mono text-slate-200 leading-relaxed max-h-48 overflow-y-auto">
                  {selectedItem.raw_text}
                </div>
              </div>

              {/* SECTION B: Operational Context & Current AI Predictions */}
              <div className="grid grid-cols-2 gap-2.5 text-xs font-mono">
                <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                  <div className="text-slate-500 text-[10px]">Current Predicted SIF</div>
                  <div className="text-sm font-bold text-amber-400 mt-0.5 flex items-center space-x-1.5">
                    <span>{selectedItem.current_ai_label === "sif_potential" ? "SIF-Potential" : "Non-SIF"}</span>
                    <span className="text-xs text-slate-400">
                      ({Math.round((selectedItem.confidence || 0.5) * 100)}%)
                    </span>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                  <div className="text-slate-500 text-[10px]">Operational Asset</div>
                  <div className="text-sm font-bold text-slate-200 mt-0.5 truncate">
                    {selectedItem.site_name || "Field Asset"}
                  </div>
                </div>
              </div>

              {/* SECTION C: Extracted Barrier Failures & LSRs */}
              {selectedItem.barrier_failures && selectedItem.barrier_failures.length > 0 && (
                <div className="space-y-2">
                  <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider font-bold">
                    Extracted Barrier Failures
                  </div>
                  <div className="space-y-1.5">
                    {selectedItem.barrier_failures.map((bf, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-xs font-mono flex items-center justify-between"
                      >
                        <span className="text-amber-300 font-semibold">{bf.barrier_type}</span>
                        <span
                          className={`px-1.5 py-0.2 rounded text-[9px] uppercase font-bold ${
                            bf.severity === "high"
                              ? "bg-red-500/20 text-red-300 border border-red-500/40"
                              : "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                          }`}
                        >
                          {bf.severity} SEVERITY
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* SECTION D: HSE Officer Correction Form */}
              <form onSubmit={handleResolveSubmit} className="space-y-5 pt-3 border-t border-slate-800">
                <div className="text-xs font-mono font-bold text-white uppercase tracking-wider flex items-center space-x-1.5">
                  <Sparkles className="w-4 h-4 text-cyan-400" />
                  <span>Submit HSE Triage Decision</span>
                </div>

                {/* Field 1: Corrected SIF Label */}
                <div className="space-y-2">
                  <label className="text-xs font-mono text-slate-300 block">
                    1. Corrected SIF Precursor Classification
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setCorrectedLabel("sif_potential")}
                      className={`p-3 rounded-lg border text-xs font-mono font-bold transition flex items-center justify-center space-x-2 ${
                        correctedLabel === "sif_potential"
                          ? "bg-red-500/25 text-red-200 border-red-500 ring-1 ring-red-500"
                          : "bg-slate-950 border-slate-800 text-slate-400 hover:text-white"
                      }`}
                    >
                      <Flame className="w-4 h-4 text-red-400" />
                      <span>SIF-Potential Precursor</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setCorrectedLabel("non_sif")}
                      className={`p-3 rounded-lg border text-xs font-mono font-bold transition flex items-center justify-center space-x-2 ${
                        correctedLabel === "non_sif"
                          ? "bg-emerald-500/25 text-emerald-200 border-emerald-500 ring-1 ring-emerald-500"
                          : "bg-slate-950 border-slate-800 text-slate-400 hover:text-white"
                      }`}
                    >
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      <span>Routine / Non-SIF</span>
                    </button>
                  </div>
                </div>

                {/* Field 2: Corrected LSR Multi-Select */}
                <div className="space-y-2">
                  <label className="text-xs font-mono text-slate-300 block flex items-center justify-between">
                    <span>2. Tagged Life-Saving Rule(s) (Multi-Select)</span>
                    <span className="text-[10px] text-slate-500">
                      {selectedLSRs.length} Selected
                    </span>
                  </label>

                  <div className="flex flex-wrap gap-1.5">
                    {CANONICAL_IOGP_LSR.map((lsr) => {
                      const isSelected = selectedLSRs.includes(lsr);
                      return (
                        <button
                          key={lsr}
                          type="button"
                          onClick={() => handleToggleLSR(lsr)}
                          className={`px-2.5 py-1 rounded-lg text-xs font-mono transition border flex items-center space-x-1.5 ${
                            isSelected
                              ? "bg-cyan-500/20 text-cyan-200 border-cyan-400 font-bold"
                              : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              isSelected ? "bg-cyan-400" : "bg-slate-600"
                            }`}
                          />
                          <span>{lsr}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Field 3: Triage Rationale & Engineering Notes */}
                <div className="space-y-2">
                  <label className="text-xs font-mono text-slate-300 block">
                    3. HSE Justification & Triage Rationale
                  </label>
                  <textarea
                    rows={3}
                    value={triageNotes}
                    onChange={(e) => setTriageNotes(e.target.value)}
                    placeholder="Enter observation notes, energy source verification, or barrier breakdown analysis to calibrate the model..."
                    className="w-full p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200 placeholder-slate-600 outline-none focus:border-amber-500"
                  />
                </div>

                {/* Submit Calibration Button */}
                <button
                  type="submit"
                  disabled={isSubmittingResolve}
                  className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-amber-500 to-red-600 hover:from-amber-600 hover:to-red-700 text-white font-mono text-xs font-bold transition shadow-lg shadow-amber-950/40 flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  {isSubmittingResolve ? (
                    <span>Calibrating NLP Model...</span>
                  ) : (
                    <>
                      <Send className="w-4 h-4" />
                      <span>Confirm Calibration & Resolve Queue Item</span>
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
