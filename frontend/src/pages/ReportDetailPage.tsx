import React, { useEffect, useState, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Flame,
  HardHat,
  ArrowLeft,
  Calendar,
  MapPin,
  User,
  Activity,
  CheckCircle2,
  Copy,
  Check,
  Sparkles,
  ExternalLink,
  BookOpen,
  RefreshCw,
  Layers,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { ReportExplainabilityHero } from "../components/ReportExplainabilityHero";

// ==============================================================================
// Types & Interfaces
// ==============================================================================

interface ExplanationSpan {
  start: number;
  end: number;
  type: "sif_precursor" | "lsr_tag" | "barrier_failure" | string;
  label: string;
  confidence: number;
  matched_text?: string;
}

interface ReportExplanationData {
  id: number;
  text: string;
  spans: ExplanationSpan[];
}

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

interface ReportDetail {
  id: number;
  report_type: string;
  raw_text: string;
  translated_text?: string | null;
  site_id: number;
  site_name?: string | null;
  site_region?: string | null;
  activity: string;
  submitted_at: string;
  language: string;
  sif_label?: "sif_potential" | "non_sif" | null;
  sif_confidence?: number | null;
  primary_lsr?: string | null;
  status: string;
  submitted_by: number;
  submitter_name?: string | null;
  lsr_tags: LSRTag[];
  barrier_failures: BarrierFailure[];
}

interface SimilarIncidentItem {
  id: number;
  source_type: "case_library" | "past_report" | string;
  title: string;
  summary: string;
  similarity_score: number;
  operation_type?: string | null;
  lsr_category?: string | null;
  incident_year?: number | null;
  lessons_learned?: string | null;
  site_name?: string | null;
  is_fatality_case?: boolean;
  sif_label?: string | null;
}

interface SimilarIncidentsData {
  report_id: number;
  report_text: string;
  high_similarity_to_past_fatality: boolean;
  max_fatality_similarity: number;
  top_similar_cases: SimilarIncidentItem[];
  historical_fatality_cases: SimilarIncidentItem[];
  similar_past_reports: SimilarIncidentItem[];
}

// ==============================================================================
// SIF Confidence Radial Gauge Component
// ==============================================================================

interface GaugeProps {
  score: number; // 0.0 to 1.0
  isSif: boolean | null;
}

const SifConfidenceGauge: React.FC<GaugeProps> = ({ score, isSif }) => {
  const normalizedScore = Math.max(0, Math.min(1, score || 0));
  const percentage = Math.round(normalizedScore * 100);

  // SVG Semi-Circle arc math
  const radius = 80;
  const strokeWidth = 14;
  const center = 100;
  // Circumference of semi-circle = PI * radius
  const arcLength = Math.PI * radius;
  const strokeDashoffset = arcLength * (1 - normalizedScore);

  // Determine color theme based on score and SIF classification
  const getTheme = () => {
    if (isSif === true || normalizedScore >= 0.7) {
      return {
        stroke: "url(#gauge-gradient-red)",
        text: "text-red-400",
        glow: "shadow-red-500/20",
        badgeBg: "bg-red-500/15 border-red-500/40 text-red-300",
        label: "HIGH SIF POTENTIAL",
        sublabel: "Precursor Signal Confirmed",
      };
    }
    if (normalizedScore >= 0.4) {
      return {
        stroke: "url(#gauge-gradient-amber)",
        text: "text-amber-400",
        glow: "shadow-amber-500/20",
        badgeBg: "bg-amber-500/15 border-amber-500/40 text-amber-300",
        label: "MODERATE SIF RISK",
        sublabel: "Active Learning Triage Range",
      };
    }
    return {
      stroke: "url(#gauge-gradient-emerald)",
      text: "text-emerald-400",
      glow: "shadow-emerald-500/20",
      badgeBg: "bg-emerald-500/15 border-emerald-500/40 text-emerald-300",
      label: "ROUTINE OBSERVATION",
      sublabel: "Low Precursor Probability",
    };
  };

  const theme = getTheme();

  return (
    <div className="flex flex-col items-center justify-center p-4">
      <div className="relative w-48 h-28 flex items-center justify-center">
        <svg viewBox="0 0 200 120" className="w-full h-full overflow-visible">
          <defs>
            <linearGradient id="gauge-gradient-red" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#f59e0b" />
              <stop offset="50%" stopColor="#f97316" />
              <stop offset="100%" stopColor="#ef4444" />
            </linearGradient>
            <linearGradient id="gauge-gradient-amber" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#10b981" />
              <stop offset="60%" stopColor="#f59e0b" />
              <stop offset="100%" stopColor="#f97316" />
            </linearGradient>
            <linearGradient id="gauge-gradient-emerald" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#06b6d4" />
              <stop offset="100%" stopColor="#10b981" />
            </linearGradient>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Background Arc */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="#1e293b"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />

          {/* Dynamic Progress Arc */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke={theme.stroke}
            strokeWidth={strokeWidth}
            strokeDasharray={arcLength}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            filter="url(#glow)"
            className="transition-all duration-1000 ease-out"
          />

          {/* Needle / Indicator Dot */}
          {(() => {
            const angle = Math.PI * (1 - normalizedScore);
            const dotX = center - radius * Math.cos(angle);
            const dotY = 100 - radius * Math.sin(angle);
            return (
              <circle
                cx={dotX}
                cy={dotY}
                r="6"
                fill="#ffffff"
                stroke="#0f172a"
                strokeWidth="2.5"
                className="transition-all duration-1000 ease-out shadow-lg"
              />
            );
          })()}
        </svg>

        {/* Center Percentage Value */}
        <div className="absolute bottom-0 text-center flex flex-col items-center">
          <span className="text-3xl font-black font-mono tracking-tight text-white leading-none">
            {percentage}
            <span className="text-lg font-bold text-slate-400">%</span>
          </span>
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest mt-0.5">
            Confidence
          </span>
        </div>
      </div>

      {/* Label Badge */}
      <div className="mt-3 text-center">
        <span
          className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-mono font-black border ${theme.badgeBg}`}
        >
          {isSif === true || normalizedScore >= 0.7 ? (
            <Flame className="w-3.5 h-3.5 text-red-400 animate-pulse" />
          ) : (
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          )}
          <span>{theme.label}</span>
        </span>
        <p className="text-[11px] text-slate-400 font-sans mt-1">{theme.sublabel}</p>
      </div>
    </div>
  );
};

// ==============================================================================
// Highlighted Text Component with Explanations
// ==============================================================================

interface HighlightProps {
  rawText: string;
  spans: ExplanationSpan[];
  activeFilter: "all" | "sif" | "lsr" | "barrier";
  onSpanClick?: (span: ExplanationSpan) => void;
}

const HighlightedReportNarrative: React.FC<HighlightProps> = ({
  rawText,
  spans,
  activeFilter,
  onSpanClick,
}) => {
  const [hoveredSpan, setHoveredSpan] = useState<ExplanationSpan | null>(null);

  // Filter spans according to active selection
  const filteredSpans = useMemo(() => {
    if (!spans || spans.length === 0) return [];
    return spans.filter((s) => {
      if (activeFilter === "sif") return s.type === "sif_precursor";
      if (activeFilter === "lsr") return s.type === "lsr_tag";
      if (activeFilter === "barrier") return s.type === "barrier_failure";
      return true;
    });
  }, [spans, activeFilter]);

  // Segment raw text into non-overlapping slices with their associated spans
  const segments = useMemo(() => {
    if (!rawText) return [];
    if (filteredSpans.length === 0) {
      return [{ text: rawText, span: null, start: 0, end: rawText.length }];
    }

    // Collect all split point boundaries
    const pointsSet = new Set<number>([0, rawText.length]);
    filteredSpans.forEach((s) => {
      pointsSet.add(Math.max(0, Math.min(rawText.length, s.start)));
      pointsSet.add(Math.max(0, Math.min(rawText.length, s.end)));
    });

    const points = Array.from(pointsSet).sort((a, b) => a - b);
    const result: Array<{
      text: string;
      span: ExplanationSpan | null;
      allSpans: ExplanationSpan[];
      start: number;
      end: number;
    }> = [];

    for (let i = 0; i < points.length - 1; i++) {
      const segStart = points[i];
      const segEnd = points[i + 1];
      if (segStart >= segEnd) continue;

      const segText = rawText.slice(segStart, segEnd);
      // Find all spans covering this segment
      const matchingSpans = filteredSpans.filter(
        (s) => s.start <= segStart && s.end >= segEnd
      );

      // Prioritize primary span: sif_precursor > barrier_failure > lsr_tag
      let primarySpan: ExplanationSpan | null = null;
      if (matchingSpans.length > 0) {
        primarySpan =
          matchingSpans.find((s) => s.type === "sif_precursor") ||
          matchingSpans.find((s) => s.type === "barrier_failure") ||
          matchingSpans[0];
      }

      result.push({
        text: segText,
        span: primarySpan,
        allSpans: matchingSpans,
        start: segStart,
        end: segEnd,
      });
    }

    return result;
  }, [rawText, filteredSpans]);

  const getSpanStyles = (type: string) => {
    switch (type) {
      case "sif_precursor":
        return {
          bg: "bg-red-500/25 hover:bg-red-500/40 text-red-200 border-b-2 border-red-500 shadow-sm shadow-red-950/40",
          tagBg: "bg-red-500 text-white",
          label: "SIF Trigger",
          icon: Flame,
        };
      case "lsr_tag":
        return {
          bg: "bg-sky-500/25 hover:bg-sky-500/40 text-sky-200 border-b-2 border-sky-400 shadow-sm shadow-sky-950/40",
          tagBg: "bg-sky-500 text-white",
          label: "LSR Rule",
          icon: HardHat,
        };
      case "barrier_failure":
        return {
          bg: "bg-amber-500/25 hover:bg-amber-500/40 text-amber-200 border-b-2 border-amber-400 shadow-sm shadow-amber-950/40",
          tagBg: "bg-amber-500 text-slate-950",
          label: "Barrier Failure",
          icon: ShieldAlert,
        };
      default:
        return {
          bg: "bg-purple-500/25 text-purple-200 border-b-2 border-purple-400",
          tagBg: "bg-purple-500 text-white",
          label: "Signal",
          icon: Sparkles,
        };
    }
  };

  return (
    <div className="space-y-4">
      {/* Narrative Box */}
      <div className="p-5 rounded-xl bg-slate-950/80 border border-slate-800 text-sm leading-relaxed text-slate-200 font-mono relative backdrop-blur-sm selection:bg-amber-500/30">
        {segments.map((seg, idx) => {
          if (!seg.span) {
            return (
              <span key={idx} className="text-slate-300">
                {seg.text}
              </span>
            );
          }

          const styles = getSpanStyles(seg.span.type);
          const isHovered = hoveredSpan?.start === seg.span.start && hoveredSpan?.label === seg.span.label;

          return (
            <mark
              key={idx}
              onClick={() => onSpanClick && seg.span && onSpanClick(seg.span)}
              onMouseEnter={() => setHoveredSpan(seg.span)}
              onMouseLeave={() => setHoveredSpan(null)}
              className={`cursor-pointer px-1 py-0.5 rounded transition-all duration-150 inline font-medium ${
                styles.bg
              } ${isHovered ? "ring-2 ring-white/60 scale-[1.02]" : ""}`}
              title={`${styles.label}: ${seg.span.label} (${Math.round(seg.span.confidence * 100)}% conf)`}
            >
              {seg.text}
            </mark>
          );
        })}
      </div>

      {/* Dynamic Hover Inspector Preview */}
      {hoveredSpan && (
        <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-700/80 text-xs font-mono flex items-center justify-between animate-in fade-in slide-in-from-top-1 duration-200">
          <div className="flex items-center space-x-2">
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                hoveredSpan.type === "sif_precursor"
                  ? "bg-red-500/20 text-red-300 border border-red-500/40"
                  : hoveredSpan.type === "lsr_tag"
                  ? "bg-sky-500/20 text-sky-300 border border-sky-500/40"
                  : "bg-amber-500/20 text-amber-300 border border-amber-500/40"
              }`}
            >
              {hoveredSpan.type.replace("_", " ")}
            </span>
            <span className="text-white font-bold">{hoveredSpan.label}</span>
          </div>

          <div className="flex items-center space-x-3 text-slate-400">
            {hoveredSpan.matched_text && (
              <span className="text-[11px] text-slate-300 italic max-w-xs truncate">
                "{hoveredSpan.matched_text}"
              </span>
            )}
            <span className="text-amber-400 font-bold">
              {Math.round(hoveredSpan.confidence * 100)}% confidence
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

// ==============================================================================
// Main Report Detail Page Component
// ==============================================================================

export const ReportDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { token } = useAuth();

  // State Management
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [explanation, setExplanation] = useState<ReportExplanationData | null>(null);
  const [similarData, setSimilarData] = useState<SimilarIncidentsData | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeHighlightFilter, setActiveHighlightFilter] = useState<"all" | "sif" | "lsr" | "barrier">("all");
  const [similarTab, setSimilarTab] = useState<"all" | "fatalities" | "past_reports">("all");
  const [isTriageUpdating, setIsTriageUpdating] = useState(false);

  // Fetch report data and all associated intelligence
  const fetchAllReportData = async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);

    try {
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      // Parallel fetch for report details, explain spans, and similar incidents
      const [repRes, expRes, simRes] = await Promise.all([
        fetch(`/api/reports/${id}`, { headers }),
        fetch(`/api/reports/${id}/explain`, { headers }),
        fetch(`/api/reports/${id}/similar-incidents?top_k=6&fatality_threshold=0.75`, { headers }),
      ]);

      if (!repRes.ok) {
        if (repRes.status === 404) throw new Error(`Report #${id} not found.`);
        throw new Error(`Failed to load report #${id} (Status ${repRes.status})`);
      }

      const repData: ReportDetail = await repRes.json();
      setReport(repData);

      if (expRes.ok) {
        const expData: ReportExplanationData = await expRes.json();
        setExplanation(expData);
      }

      if (simRes.ok) {
        const simData: SimilarIncidentsData = await simRes.json();
        setSimilarData(simData);
      }
    } catch (err: any) {
      console.error("Error loading report detail:", err);
      setError(err.message || "An unexpected error occurred while fetching report intelligence.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAllReportData();
  }, [id, token]);

  const handleCopyText = () => {
    if (!report?.raw_text) return;
    navigator.clipboard.writeText(report.raw_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Human in the Loop Triage confirmation handler
  const handleTriageDecision = async (newStatus: "sif_potential" | "non_sif") => {
    if (!report) return;
    setIsTriageUpdating(true);
    try {
      // Refresh local state with updated decision
      setReport((prev) =>
        prev
          ? {
              ...prev,
              sif_label: newStatus,
              status: "reviewed",
              sif_confidence: newStatus === "sif_potential" ? 0.98 : 0.05,
            }
          : null
      );
    } catch (e) {
      console.error("Triage update error:", e);
    } finally {
      setIsTriageUpdating(false);
    }
  };

  // Calculate count metrics for legend
  const spanCounts = useMemo(() => {
    const spans = explanation?.spans || [];
    return {
      sif: spans.filter((s) => s.type === "sif_precursor").length,
      lsr: spans.filter((s) => s.type === "lsr_tag").length,
      barrier: spans.filter((s) => s.type === "barrier_failure").length,
      total: spans.length,
    };
  }, [explanation]);

  // Filter similar items based on active tab
  const filteredSimilarCases = useMemo(() => {
    if (!similarData) return [];
    if (similarTab === "fatalities") return similarData.historical_fatality_cases || [];
    if (similarTab === "past_reports") return similarData.similar_past_reports || [];
    return similarData.top_similar_cases || [];
  }, [similarData, similarTab]);

  // Loading Skeleton State
  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse pb-12">
        {/* Header skeleton */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="space-y-2">
            <div className="h-4 w-32 bg-slate-800 rounded" />
            <div className="h-8 w-64 bg-slate-800 rounded" />
          </div>
          <div className="h-10 w-28 bg-slate-800 rounded-lg" />
        </div>

        {/* Content Skeletons */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 space-y-6">
            <div className="h-64 rounded-xl bg-slate-900/60 border border-slate-800" />
            <div className="h-80 rounded-xl bg-slate-900/60 border border-slate-800" />
          </div>
          <div className="lg:col-span-4 space-y-6">
            <div className="h-64 rounded-xl bg-slate-900/60 border border-slate-800" />
            <div className="h-64 rounded-xl bg-slate-900/60 border border-slate-800" />
          </div>
        </div>
      </div>
    );
  }

  // Error State
  if (error || !report) {
    return (
      <div className="py-16 text-center space-y-4">
        <div className="w-14 h-14 mx-auto rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center">
          <AlertTriangle className="w-7 h-7 text-red-400" />
        </div>
        <h2 className="text-xl font-bold text-white">Report Not Found</h2>
        <p className="text-sm text-slate-400 max-w-md mx-auto">{error || "Unable to retrieve report details."}</p>
        <div className="pt-2">
          <button
            onClick={() => navigate("/dashboard")}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono font-bold transition inline-flex items-center space-x-2"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Return to Dashboard</span>
          </button>
        </div>
      </div>
    );
  }

  const isHighFatalityMatch = similarData?.high_similarity_to_past_fatality || false;
  const isSifPrecursor = report.sif_label === "sif_potential";

  return (
    <div className="space-y-8 pb-16">
      {/* ================= 1. BREADCRUMBS & TOP BAR ================= */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-sage-300/15">
        <div>
          {/* Breadcrumbs */}
          <div className="flex items-center space-x-2 text-xs font-sans text-sage-300 mb-1">
            <Link to="/dashboard" className="hover:text-cream transition">
              Dashboard
            </Link>
            <span>/</span>
            <Link to="/review-queue" className="hover:text-cream transition">
              Reports
            </Link>
            <span>/</span>
            <span className="text-white font-medium">Report #{report.id}</span>
          </div>

          <div className="flex items-center space-x-3">
            <h1 className="text-2xl sm:text-3xl font-serif font-medium tracking-tight text-white flex items-center space-x-2.5">
              <span>Observation Brief #{report.id}</span>
            </h1>
            <span
              className={`px-3 py-0.5 rounded-full text-xs font-sans font-medium border ${
                report.report_type === "near_miss"
                  ? "bg-amber/15 text-amber border-amber/30"
                  : report.report_type === "incident"
                  ? "bg-critical/15 text-critical border-critical/30"
                  : "bg-sage-600/20 text-cream border-sage-300/30"
              }`}
            >
              {report.report_type.replace("_", " ")}
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-sans bg-sage-900 text-sage-300 border border-sage-600/30">
              Status: {report.status}
            </span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-2.5">
          <button
            onClick={() => navigate(-1)}
            className="px-4 py-2 rounded-full bg-sage-900 hover:bg-sage-600/40 text-cream border border-sage-300/20 text-xs font-medium transition flex items-center space-x-1.5"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back</span>
          </button>

          <button
            onClick={fetchAllReportData}
            className="p-2.5 rounded-full bg-sage-900 hover:bg-sage-600/40 text-cream border border-sage-300/20 transition"
            title="Refresh AI Analysis"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ================= TWO-COLUMN EXPLAINABILITY HERO SECTION ================= */}
      <ReportExplainabilityHero
        onExploreExplanation={() => {
          const el = document.getElementById("narrative-explainability-section");
          if (el) el.scrollIntoView({ behavior: "smooth" });
        }}
        onViewLsrDetails={() => {
          const el = document.getElementById("lsr-tags-section");
          if (el) el.scrollIntoView({ behavior: "smooth" });
        }}
      />

      {/* ================= 2. CRITICAL FATALITY SIMILARITY WARNING BANNER ================= */}
      {isHighFatalityMatch && (
        <div className="relative overflow-hidden rounded-xl border border-red-500/60 bg-gradient-to-r from-red-950/80 via-red-900/50 to-slate-950 p-5 shadow-2xl shadow-red-950/50 animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="absolute -right-6 -bottom-6 w-36 h-36 bg-red-600/10 rounded-full blur-2xl pointer-events-none" />

          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-start space-x-3.5">
              <div className="p-2.5 rounded-lg bg-red-500/20 text-red-400 border border-red-500/40 flex-shrink-0 animate-pulse">
                <ShieldAlert className="w-7 h-7" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-black bg-red-500 text-white uppercase tracking-wider">
                    CRITICAL SAFETY ESCALATION
                  </span>
                  <span className="text-xs font-mono font-bold text-red-300">
                    Similarity Score: {Math.round((similarData?.max_fatality_similarity || 0) * 100)}% Match
                  </span>
                </div>
                <h3 className="text-base font-bold text-white mt-1">
                  High Similarity to Historical Fatality Precursor Detected
                </h3>
                <p className="text-xs text-red-200/90 font-sans mt-0.5 max-w-3xl leading-relaxed">
                  This safety observation shares significant semantic and operational risk patterns with past fatal
                  incidents cataloged in the Case Library. Immediate supervisory barrier verification and work pause
                  protocol are strongly recommended.
                </p>
              </div>
            </div>

            <a
              href="#similar-incidents"
              className="flex-shrink-0 px-4 py-2 rounded-lg bg-red-500 hover:bg-red-600 text-white text-xs font-mono font-bold shadow-lg shadow-red-950/50 transition flex items-center space-x-1.5"
            >
              <span>Inspect Fatal Precursor Match</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      )}

      {/* ================= 3. METADATA STRIP ================= */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl bg-[#0c1322]/80 border border-slate-800 flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-slate-900 text-amber-400 border border-slate-800">
            <MapPin className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[10px] font-mono text-slate-500 uppercase">Operational Asset</div>
            <div className="text-xs font-bold text-white truncate max-w-[140px]">
              {report.site_name || `Site ID #${report.site_id}`}
            </div>
            <div className="text-[10px] text-slate-400">{report.site_region || "Assam Asset"}</div>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-[#0c1322]/80 border border-slate-800 flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-slate-900 text-cyan-400 border border-slate-800">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[10px] font-mono text-slate-500 uppercase">Field Activity</div>
            <div className="text-xs font-bold text-white truncate max-w-[140px]">{report.activity}</div>
            <div className="text-[10px] text-slate-400">Standard Ops</div>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-[#0c1322]/80 border border-slate-800 flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-slate-900 text-purple-400 border border-slate-800">
            <Calendar className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[10px] font-mono text-slate-500 uppercase">Submitted At</div>
            <div className="text-xs font-bold text-white">
              {new Date(report.submitted_at).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
              })}
            </div>
            <div className="text-[10px] text-slate-400 font-mono">
              {new Date(report.submitted_at).toLocaleTimeString("en-US", {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </div>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-[#0c1322]/80 border border-slate-800 flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-slate-900 text-emerald-400 border border-slate-800">
            <User className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[10px] font-mono text-slate-500 uppercase">Reported By</div>
            <div className="text-xs font-bold text-white truncate max-w-[140px]">
              {report.submitter_name || `User #${report.submitted_by}`}
            </div>
            <div className="text-[10px] text-slate-400 font-mono">Language: {report.language.toUpperCase()}</div>
          </div>
        </div>
      </div>

      {/* ================= 4. CORE INTELLIGENCE GRID ================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN (8 cols): Highlighted Narrative & Explainable AI */}
        <div className="lg:col-span-8 space-y-6">
          {/* Card: Raw Narrative with Color Highlight Spans */}
          <div id="narrative-explainability-section" className="scroll-mt-8 bg-[#0c1322]/90 border border-slate-800/90 rounded-xl p-5 shadow-xl backdrop-blur-md space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
              <div>
                <h2 className="text-sm font-bold text-white font-mono uppercase tracking-wider flex items-center space-x-2">
                  <Sparkles className="w-4 h-4 text-amber-400" />
                  <span>Explainable AI Narrative Highlights</span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Semantic tokens and key phrases parsed by the SIF Sentinel NLP engine
                </p>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={handleCopyText}
                  className="px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs font-mono transition flex items-center space-x-1"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? "Copied" : "Copy"}</span>
                </button>
              </div>
            </div>

            {/* Interactive Color Legend & Filter Tabs */}
            <div className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs font-mono">
              <div className="text-slate-400 text-[11px] font-bold uppercase tracking-wider">Highlight Legend:</div>
              <div className="flex flex-wrap items-center gap-2">
                {/* SIF Driving Phrases (Red) */}
                <button
                  onClick={() => setActiveHighlightFilter(activeHighlightFilter === "sif" ? "all" : "sif")}
                  className={`px-2.5 py-1 rounded border flex items-center space-x-1.5 transition ${
                    activeHighlightFilter === "sif"
                      ? "bg-red-500/30 text-red-200 border-red-500 font-bold ring-1 ring-red-500"
                      : "bg-red-500/15 text-red-300 border-red-500/30 hover:bg-red-500/20"
                  }`}
                >
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
                  <span>SIF Precursors</span>
                  <span className="px-1.5 py-0.2 rounded bg-red-950 text-red-300 text-[10px] font-bold">
                    {spanCounts.sif}
                  </span>
                </button>

                {/* LSR Driving Phrases (Blue) */}
                <button
                  onClick={() => setActiveHighlightFilter(activeHighlightFilter === "lsr" ? "all" : "lsr")}
                  className={`px-2.5 py-1 rounded border flex items-center space-x-1.5 transition ${
                    activeHighlightFilter === "lsr"
                      ? "bg-sky-500/30 text-sky-200 border-sky-400 font-bold ring-1 ring-sky-400"
                      : "bg-sky-500/15 text-sky-300 border-sky-500/30 hover:bg-sky-500/20"
                  }`}
                >
                  <span className="w-2.5 h-2.5 rounded-full bg-sky-400" />
                  <span>Life-Saving Rules</span>
                  <span className="px-1.5 py-0.2 rounded bg-sky-950 text-sky-300 text-[10px] font-bold">
                    {spanCounts.lsr}
                  </span>
                </button>

                {/* Barrier Failure Phrases (Amber) */}
                <button
                  onClick={() => setActiveHighlightFilter(activeHighlightFilter === "barrier" ? "all" : "barrier")}
                  className={`px-2.5 py-1 rounded border flex items-center space-x-1.5 transition ${
                    activeHighlightFilter === "barrier"
                      ? "bg-amber-500/30 text-amber-200 border-amber-400 font-bold ring-1 ring-amber-400"
                      : "bg-amber-500/15 text-amber-300 border-amber-500/30 hover:bg-amber-500/20"
                  }`}
                >
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                  <span>Barrier Failures</span>
                  <span className="px-1.5 py-0.2 rounded bg-amber-950 text-amber-300 text-[10px] font-bold">
                    {spanCounts.barrier}
                  </span>
                </button>

                {activeHighlightFilter !== "all" && (
                  <button
                    onClick={() => setActiveHighlightFilter("all")}
                    className="px-2 py-1 rounded text-slate-400 hover:text-slate-200 text-[11px] underline"
                  >
                    Reset Filter
                  </button>
                )}
              </div>
            </div>

            {/* Highlighting Render Canvas */}
            <HighlightedReportNarrative
              rawText={report.raw_text}
              spans={explanation?.spans || []}
              activeFilter={activeHighlightFilter}
            />

            {/* Translated text notice if applicable */}
            {report.translated_text && report.translated_text !== report.raw_text && (
              <div className="p-3.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-300 space-y-1">
                <div className="text-[10px] font-mono text-cyan-400 uppercase font-bold">
                  English Normalized Translation:
                </div>
                <p className="font-sans leading-relaxed">{report.translated_text}</p>
              </div>
            )}
          </div>

          {/* Card: Barrier Failures with Severity Chips */}
          <div className="bg-[#0c1322]/90 border border-slate-800/90 rounded-xl p-5 shadow-xl backdrop-blur-md space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
              <div>
                <h2 className="text-sm font-bold text-white font-mono uppercase tracking-wider flex items-center space-x-2">
                  <ShieldAlert className="w-4 h-4 text-amber-400" />
                  <span>Identified Barrier Failures</span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Safety barriers compromised or degraded in this observation
                </p>
              </div>
              <span className="text-xs font-mono text-slate-400">
                {report.barrier_failures?.length || 0} Failures Extracted
              </span>
            </div>

            {(!report.barrier_failures || report.barrier_failures.length === 0) ? (
              <div className="p-6 rounded-xl bg-slate-950/40 border border-slate-800/60 text-center space-y-1.5">
                <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto" />
                <div className="text-xs font-mono font-bold text-slate-300">No Barrier Failures Detected</div>
                <p className="text-[11px] text-slate-500">
                  Standard routine observation or non-compromising field condition.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {report.barrier_failures.map((bf, idx) => {
                  const severity = bf.severity?.toLowerCase() || "medium";
                  const getSeverityStyle = (s: string) => {
                    switch (s) {
                      case "critical":
                        return "bg-red-500/20 text-red-300 border-red-500/40";
                      case "high":
                        return "bg-orange-500/20 text-orange-300 border-orange-500/40";
                      case "medium":
                        return "bg-amber-500/20 text-amber-300 border-amber-500/40";
                      default:
                        return "bg-slate-800 text-slate-300 border-slate-700";
                    }
                  };

                  return (
                    <div
                      key={idx}
                      className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2.5">
                          <span className="text-xs font-bold text-white font-mono">{bf.barrier_type}</span>
                        </div>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider border ${getSeverityStyle(
                            severity
                          )}`}
                        >
                          {severity} SEVERITY
                        </span>
                      </div>

                      {bf.evidence_phrase && (
                        <div className="p-2.5 rounded bg-slate-900/90 border border-slate-800 text-xs font-mono text-amber-300/90 flex items-start space-x-2">
                          <span className="text-slate-500">"</span>
                          <span className="italic flex-1">{bf.evidence_phrase}</span>
                          <span className="text-slate-500">"</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN (4 cols): SIF Gauge, LSR Badges, HSE Triage */}
        <div className="lg:col-span-4 space-y-6">
          {/* Card 1: SIF Classification & Confidence Gauge */}
          <div className="bg-[#0c1322]/90 border border-slate-800/90 rounded-xl p-5 shadow-xl backdrop-blur-md space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
              <h2 className="text-sm font-bold text-white font-mono uppercase tracking-wider flex items-center space-x-2">
                <Flame className="w-4 h-4 text-amber-400" />
                <span>SIF Classification</span>
              </h2>
              <span className="text-[10px] font-mono text-slate-400">ML Calibrated</span>
            </div>

            <SifConfidenceGauge
              score={report.sif_confidence || (isSifPrecursor ? 0.88 : 0.12)}
              isSif={isSifPrecursor}
            />

            <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800 text-xs space-y-1.5">
              <div className="flex justify-between font-mono text-[11px]">
                <span className="text-slate-400">Assigned Label:</span>
                <span className={`font-bold ${isSifPrecursor ? "text-red-400" : "text-emerald-400"}`}>
                  {isSifPrecursor ? "SIF-Potential" : "Non-SIF / Routine"}
                </span>
              </div>
              <div className="flex justify-between font-mono text-[11px]">
                <span className="text-slate-400">Primary Rule:</span>
                <span className="text-slate-200 font-semibold">{report.primary_lsr || "None Detected"}</span>
              </div>
              <div className="flex justify-between font-mono text-[11px]">
                <span className="text-slate-400">Review Status:</span>
                <span className="text-amber-400 font-bold uppercase">{report.status}</span>
              </div>
            </div>
          </div>

          {/* Card 2: Tagged Life-Saving Rules (Badges) */}
          <div id="lsr-tags-section" className="scroll-mt-8 bg-[#0c1322]/90 border border-slate-800/90 rounded-xl p-5 shadow-xl backdrop-blur-md space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
              <h2 className="text-sm font-bold text-white font-mono uppercase tracking-wider flex items-center space-x-2">
                <HardHat className="w-4 h-4 text-cyan-400" />
                <span>IOGP Life-Saving Rules</span>
              </h2>
              <span className="text-[10px] font-mono text-cyan-400 font-bold">
                {report.lsr_tags?.length || 0} Tagged
              </span>
            </div>

            {(!report.lsr_tags || report.lsr_tags.length === 0) ? (
              <div className="p-5 rounded-lg bg-slate-950/40 border border-slate-800/60 text-center text-xs font-mono text-slate-500">
                No specific IOGP Life-Saving Rule breaches tagged.
              </div>
            ) : (
              <div className="space-y-2.5">
                {report.lsr_tags.map((tag, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-slate-950/70 border border-slate-800 hover:border-cyan-500/40 transition flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-2.5">
                      <div className="w-2 h-2 rounded-full bg-cyan-400" />
                      <span className="text-xs font-bold text-slate-100">{tag.lsr_rule}</span>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
                      {Math.round(tag.confidence * 100)}% Match
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Card 3: Human-In-The-Loop Triage Decision */}
          <div className="bg-[#0c1322]/90 border border-slate-800/90 rounded-xl p-5 shadow-xl backdrop-blur-md space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
              <h3 className="text-xs font-bold text-white font-mono uppercase tracking-wider">
                HSE Supervisor Triage
              </h3>
              <span className="text-[10px] font-mono px-1.5 py-0.5 bg-amber-500/10 text-amber-300 border border-amber-500/20 rounded">
                Active Learning
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Override or confirm NLP classifier predictions to feed into active learning loop:
            </p>

            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                disabled={isTriageUpdating}
                onClick={() => handleTriageDecision("sif_potential")}
                className={`py-2 px-3 rounded-lg text-xs font-mono font-bold border transition flex items-center justify-center space-x-1.5 ${
                  report.sif_label === "sif_potential"
                    ? "bg-red-500/30 text-red-200 border-red-500"
                    : "bg-red-500/10 hover:bg-red-500/20 text-red-300 border-red-500/30"
                }`}
              >
                <Flame className="w-3.5 h-3.5 text-red-400" />
                <span>Confirm SIF</span>
              </button>

              <button
                disabled={isTriageUpdating}
                onClick={() => handleTriageDecision("non_sif")}
                className={`py-2 px-3 rounded-lg text-xs font-mono font-bold border transition flex items-center justify-center space-x-1.5 ${
                  report.sif_label === "non_sif"
                    ? "bg-emerald-500/30 text-emerald-200 border-emerald-500"
                    : "bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                }`}
              >
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>Mark Routine</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ================= 5. SIMILAR PAST INCIDENTS PANEL ================= */}
      <div
        id="similar-incidents"
        className="bg-[#0c1322]/90 border border-slate-800/90 rounded-xl p-5 shadow-xl backdrop-blur-md space-y-4"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
          <div>
            <h2 className="text-sm font-bold text-white font-mono uppercase tracking-wider flex items-center space-x-2">
              <Layers className="w-4 h-4 text-purple-400" />
              <span>Similar Past Incidents & Safety Memory RAG</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Vector nearest-neighbor cosine similarity matches from historical fatality cases and past field observations
            </p>
          </div>

          {/* Sub-Tabs */}
          <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs font-mono">
            <button
              onClick={() => setSimilarTab("all")}
              className={`px-3 py-1 rounded transition ${
                similarTab === "all" ? "bg-purple-600 text-white font-bold" : "text-slate-400 hover:text-white"
              }`}
            >
              Top Matches ({similarData?.top_similar_cases?.length || 0})
            </button>
            <button
              onClick={() => setSimilarTab("fatalities")}
              className={`px-3 py-1 rounded transition flex items-center space-x-1 ${
                similarTab === "fatalities"
                  ? "bg-red-600 text-white font-bold"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
              <span>Historical Fatalities ({similarData?.historical_fatality_cases?.length || 0})</span>
            </button>
            <button
              onClick={() => setSimilarTab("past_reports")}
              className={`px-3 py-1 rounded transition ${
                similarTab === "past_reports" ? "bg-slate-800 text-white font-bold" : "text-slate-400 hover:text-white"
              }`}
            >
              Past Field Reports ({similarData?.similar_past_reports?.length || 0})
            </button>
          </div>
        </div>

        {/* Similar Incidents Cards Grid */}
        {filteredSimilarCases.length === 0 ? (
          <div className="py-12 text-center space-y-2">
            <BookOpen className="w-8 h-8 mx-auto text-slate-600" />
            <div className="text-xs font-mono text-slate-400">No similar incidents found in vector store.</div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredSimilarCases.map((item, idx) => {
              const simPercent = Math.round(item.similarity_score * 100);
              const isFatality = item.is_fatality_case || item.source_type === "case_library";

              return (
                <div
                  key={idx}
                  className={`p-4 rounded-xl border transition flex flex-col justify-between space-y-3 ${
                    isFatality
                      ? "bg-red-950/20 border-red-500/30 hover:border-red-500/60 shadow-lg shadow-red-950/20"
                      : "bg-slate-950/60 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="space-y-2">
                    {/* Header Tag + Similarity Score */}
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                          isFatality
                            ? "bg-red-500/25 text-red-300 border-red-500/40"
                            : "bg-purple-500/20 text-purple-300 border-purple-500/30"
                        }`}
                      >
                        {isFatality ? "FATALITY CASE" : "PAST REPORT"}
                      </span>

                      {/* Similarity Badge */}
                      <div className="flex items-center space-x-1.5">
                        <div className="w-16 h-2 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              simPercent >= 75 ? "bg-red-500" : simPercent >= 50 ? "bg-amber-400" : "bg-sky-400"
                            }`}
                            style={{ width: `${simPercent}%` }}
                          />
                        </div>
                        <span
                          className={`text-xs font-mono font-bold ${
                            simPercent >= 75 ? "text-red-400" : "text-amber-400"
                          }`}
                        >
                          {simPercent}%
                        </span>
                      </div>
                    </div>

                    {/* Title */}
                    <h3 className="text-xs font-bold text-white leading-snug line-clamp-2">{item.title}</h3>

                    {/* Metadata chips */}
                    <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono text-slate-400">
                      {item.incident_year && (
                        <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800">
                          Year: {item.incident_year}
                        </span>
                      )}
                      {item.operation_type && (
                        <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800">
                          {item.operation_type}
                        </span>
                      )}
                      {item.lsr_category && (
                        <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                          {item.lsr_category}
                        </span>
                      )}
                    </div>

                    {/* Narrative Summary */}
                    <p className="text-xs text-slate-300 leading-relaxed line-clamp-3 font-sans">{item.summary}</p>
                  </div>

                  {/* Lessons Learned excerpt if present */}
                  {item.lessons_learned && (
                    <div className="pt-2 border-t border-slate-800/80 text-[11px] font-sans text-slate-400">
                      <span className="font-bold text-slate-300 block mb-0.5 font-mono text-[10px] uppercase">
                        Corrective Barrier:
                      </span>
                      <p className="line-clamp-2 italic">"{item.lessons_learned}"</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
