import React, { useEffect, useState, useMemo } from "react";
import {
  MapPin,
  Trophy,
  Minus,
  Sliders,
  Sparkles,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  Search,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import { useAuth } from "../context/AuthContext";
import { FeatureCardsSection } from "../components/FeatureCardsSection";

// ==============================================================================
// Types & Interfaces
// ==============================================================================

interface SiteBarrierBreakdown {
  barrier_type: string;
  failure_count: number;
  severity_weight: number;
  percentage: number;
}

interface SiteSIIRankingItem {
  rank: number;
  site_id: number;
  site_name: string;
  region: string;
  operation_type: string;
  current_sii: number;
  previous_sii: number;
  sii_delta: number;
  sif_density: number;
  total_reports: number;
  sif_reports_count: number;
  top_barrier_failure?: string | null;
  status_tier: "High Performer" | "Stable" | "Attention Required" | "Critical Risk" | string;
  trend: "rising" | "stable" | "falling" | string;
  barrier_breakdown: SiteBarrierBreakdown[];
}

interface SIITrendPoint {
  period: string;
  date: string;
  sii_score: number;
  sif_density: number;
  barrier_recurrence_score: number;
  total_reports: number;
  sif_count: number;
}

interface SiteSIITrendResponse {
  site_id: number;
  site_name: string;
  region: string;
  operation_type: string;
  current_sii: number;
  trend: SIITrendPoint[];
}

interface BarrierImpactDetail {
  barrier_type: string;
  original_failures: number;
  reduced_failures: number;
  sii_contribution: number;
}

interface WhatIfSimulationResponse {
  site_id: number;
  site_name: string;
  current_sii: number;
  projected_sii: number;
  sii_gain: number;
  current_rank: number;
  projected_rank: number;
  barrier_impacts: BarrierImpactDetail[];
  explanation: string;
}

// ==============================================================================
// Main Sites Page Component
// ==============================================================================

export const SitesPage: React.FC = () => {
  const { token } = useAuth();

  // State Management
  const [rankingList, setRankingList] = useState<SiteSIIRankingItem[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<number | null>(null);
  const [siteTrend, setSiteTrend] = useState<SiteSIITrendResponse | null>(null);
  const [simulationResult, setSimulationResult] = useState<WhatIfSimulationResponse | null>(null);

  const [isLoadingRanking, setIsLoadingRanking] = useState(true);
  const [isLoadingTrend, setIsLoadingTrend] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState("");
  const [regionFilter, setRegionFilter] = useState<string>("all");

  // What-If Sliders State: mapping of barrier_type -> reduction % (0 to 100)
  const [barrierReductions, setBarrierReductions] = useState<Record<string, number>>({});

  // 1. Fetch SII Leaderboard
  const fetchRankingData = async () => {
    setIsLoadingRanking(true);
    try {
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch("/api/sites/sii-ranking", { headers });
      if (res.ok) {
        const data: SiteSIIRankingItem[] = await res.json();
        setRankingList(data);
        if (data.length > 0 && selectedSiteId === null) {
          setSelectedSiteId(data[0].site_id);
        }
      }
    } catch (e) {
      console.error("Error fetching SII ranking:", e);
    } finally {
      setIsLoadingRanking(false);
    }
  };

  // 2. Fetch Trend History for Selected Site
  const fetchSiteTrend = async (siteId: number) => {
    setIsLoadingTrend(true);
    try {
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`/api/sites/${siteId}/sii-trend`, { headers });
      if (res.ok) {
        const data: SiteSIITrendResponse = await res.json();
        setSiteTrend(data);
      }
    } catch (e) {
      console.error("Error fetching site trend:", e);
    } finally {
      setIsLoadingTrend(false);
    }
  };

  useEffect(() => {
    fetchRankingData();
  }, [token]);

  useEffect(() => {
    if (selectedSiteId !== null) {
      fetchSiteTrend(selectedSiteId);

      // Initialize default reduction slider targets for this site
      const selectedItem = rankingList.find((s) => s.site_id === selectedSiteId);
      const initialReductions: Record<string, number> = {};
      if (selectedItem?.barrier_breakdown) {
        selectedItem.barrier_breakdown.forEach((b) => {
          initialReductions[b.barrier_type] = 0;
        });
      }
      setBarrierReductions(initialReductions);
      setSimulationResult(null);
    }
  }, [selectedSiteId]);

  // Selected site object from leaderboard
  const selectedSite = useMemo(() => {
    return rankingList.find((s) => s.site_id === selectedSiteId) || rankingList[0] || null;
  }, [rankingList, selectedSiteId]);

  // Client-Side + Server-Side What-If Calculation
  const runWhatIfSimulation = async (reductions: Record<string, number>) => {
    if (!selectedSiteId || !selectedSite) return;

    // Fast client-side projection
    const baseSii = selectedSite.current_sii;
    let weightedReduction = 0;
    let totalFailures = 0;

    selectedSite.barrier_breakdown.forEach((b) => {
      totalFailures += b.failure_count;
      const red = reductions[b.barrier_type] || 0;
      weightedReduction += (red / 100) * b.failure_count * (b.severity_weight || 1.5);
    });

    const gain = Math.min(30.0, (weightedReduction * 12.0) / Math.max(selectedSite.total_reports, 1));
    const clientProj = Math.min(100.0, Math.round((baseSii + gain) * 10) / 10);

    // Update client preview immediately
    setSimulationResult({
      site_id: selectedSite.site_id,
      site_name: selectedSite.site_name,
      current_sii: baseSii,
      projected_sii: clientProj,
      sii_gain: Math.round((clientProj - baseSii) * 10) / 10,
      current_rank: selectedSite.rank,
      projected_rank: clientProj >= 90.0 ? 1 : clientProj >= 80.0 ? 2 : selectedSite.rank,
      barrier_impacts: selectedSite.barrier_breakdown.map((b) => ({
        barrier_type: b.barrier_type,
        original_failures: b.failure_count,
        reduced_failures: Math.round(b.failure_count * (1 - (reductions[b.barrier_type] || 0) / 100) * 10) / 10,
        sii_contribution: Math.round(((reductions[b.barrier_type] || 0) / 100) * b.failure_count * 1.5 * 10) / 10,
      })),
      explanation: `Projected +${Math.round((clientProj - baseSii) * 10) / 10} point increase in Safety Index by reducing targeted barrier failures.`,
    });

    // Perform server-side call for strict consistency
    try {
      setIsSimulating(true);
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`/api/sites/${selectedSiteId}/simulate`, {
        method: "POST",
        headers,
        body: JSON.stringify({ reductions }),
      });

      if (res.ok) {
        const data: WhatIfSimulationResponse = await res.json();
        setSimulationResult(data);
      }
    } catch (e) {
      console.warn("Server simulation fallback:", e);
    } finally {
      setIsSimulating(false);
    }
  };

  const handleSliderChange = (barrierType: string, value: number) => {
    const updated = { ...barrierReductions, [barrierType]: value };
    setBarrierReductions(updated);
    runWhatIfSimulation(updated);
  };

  const handleApplyPreset = (percent: number) => {
    if (!selectedSite) return;
    const updated: Record<string, number> = {};
    selectedSite.barrier_breakdown.forEach((b) => {
      updated[b.barrier_type] = percent;
    });
    setBarrierReductions(updated);
    runWhatIfSimulation(updated);
  };

  const handleResetSliders = () => {
    if (!selectedSite) return;
    const updated: Record<string, number> = {};
    selectedSite.barrier_breakdown.forEach((b) => {
      updated[b.barrier_type] = 0;
    });
    setBarrierReductions(updated);
    runWhatIfSimulation(updated);
  };

  // Regions list for filtering
  const availableRegions = useMemo(() => {
    const set = new Set<string>();
    rankingList.forEach((s) => {
      if (s.region) set.add(s.region);
    });
    return Array.from(set);
  }, [rankingList]);

  // Filtered leaderboard list
  const filteredRankingList = useMemo(() => {
    return rankingList.filter((item) => {
      const matchesSearch =
        !searchQuery ||
        item.site_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.operation_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.region.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesRegion = regionFilter === "all" || item.region === regionFilter;
      return matchesSearch && matchesRegion;
    });
  }, [rankingList, searchQuery, regionFilter]);

  const getTierBadge = (tier: string) => {
    switch (tier) {
      case "High Performer":
        return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
      case "Stable":
        return "bg-cyan-500/15 text-cyan-300 border-cyan-500/30";
      case "Attention Required":
        return "bg-amber-500/15 text-amber-300 border-amber-500/30";
      case "Critical Risk":
        return "bg-red-500/15 text-red-300 border-red-500/30";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <div className="space-y-6 pb-16">
      {/* ================= 1. TOP HEADER ================= */}
      <div className="border-b border-slate-800/80 pb-3 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-2xl font-black tracking-tight text-white flex items-center space-x-2">
              <span>Asset Safety Intelligence & SII Leaderboard</span>
            </h1>
            <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 rounded">
              SAFETY INDEX
            </span>
          </div>
          <p className="text-xs text-slate-400 font-normal mt-0.5">
            Dynamic Safety Improvement Index (SII) ranking, 6-month trend trajectory, and What-If barrier reduction simulator
          </p>
        </div>

        <button
          onClick={() => {
            fetchRankingData();
            if (selectedSiteId) fetchSiteTrend(selectedSiteId);
          }}
          className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs font-mono font-bold transition flex items-center space-x-1.5 shrink-0"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      {/* ================= 2. LEADERBOARD TABLE & RANKING ================= */}
      <div className="bg-[#0c1322]/90 border border-slate-800/90 rounded-xl overflow-hidden shadow-xl backdrop-blur-md space-y-4 p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
          <div>
            <h2 className="text-sm font-bold text-white font-mono uppercase tracking-wider flex items-center space-x-2">
              <Trophy className="w-4 h-4 text-amber-400" />
              <span>Asset Safety Improvement Index (SII) Leaderboard</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Ranked from highest safety performance (Rank 1) to critical attention required
            </p>
          </div>

          {/* Search & Region Filters */}
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter rig or asset..."
                className="pl-8 pr-3 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 outline-none focus:border-amber-500/60"
              />
            </div>

            <select
              value={regionFilter}
              onChange={(e) => setRegionFilter(e.target.value)}
              className="py-1 px-2.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 outline-none focus:border-amber-500/60"
            >
              <option value="all">All Regions</option>
              {availableRegions.map((reg) => (
                <option key={reg} value={reg}>
                  {reg}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Leaderboard Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-[11px] font-mono text-slate-400 uppercase tracking-wider bg-slate-950/40">
                <th className="py-3 px-3 text-center w-14">Rank</th>
                <th className="py-3 px-4">Installation / Rig Name</th>
                <th className="py-3 px-4">Region / Operation</th>
                <th className="py-3 px-4 text-center">Safety Index (SII)</th>
                <th className="py-3 px-4 text-center">6-Mo $\Delta$ Trend</th>
                <th className="py-3 px-4 text-center">SIF Density</th>
                <th className="py-3 px-4">Top Compromised Barrier</th>
                <th className="py-3 px-4 text-right">Performance Tier</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-xs">
              {isLoadingRanking ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="py-4 px-3 text-center">
                      <div className="h-4 w-6 bg-slate-800 rounded mx-auto" />
                    </td>
                    <td className="py-4 px-4">
                      <div className="h-4 w-40 bg-slate-800 rounded" />
                    </td>
                    <td className="py-4 px-4">
                      <div className="h-4 w-32 bg-slate-800 rounded" />
                    </td>
                    <td className="py-4 px-4 text-center">
                      <div className="h-6 w-16 bg-slate-800 rounded mx-auto" />
                    </td>
                    <td className="py-4 px-4 text-center">
                      <div className="h-4 w-12 bg-slate-800 rounded mx-auto" />
                    </td>
                    <td className="py-4 px-4 text-center">
                      <div className="h-4 w-10 bg-slate-800 rounded mx-auto" />
                    </td>
                    <td className="py-4 px-4">
                      <div className="h-4 w-36 bg-slate-800 rounded" />
                    </td>
                    <td className="py-4 px-4 text-right">
                      <div className="h-5 w-24 bg-slate-800 rounded ml-auto" />
                    </td>
                  </tr>
                ))
              ) : filteredRankingList.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500 font-mono">
                    No operational assets match the current filter criteria.
                  </td>
                </tr>
              ) : (
                filteredRankingList.map((item) => {
                  const isSelected = selectedSiteId === item.site_id;
                  const siiColor =
                    item.current_sii >= 80.0
                      ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/30"
                      : item.current_sii >= 65.0
                      ? "text-amber-400 bg-amber-500/10 border-amber-500/30"
                      : "text-red-400 bg-red-500/10 border-red-500/30";

                  return (
                    <tr
                      key={item.site_id}
                      onClick={() => setSelectedSiteId(item.site_id)}
                      className={`cursor-pointer transition group ${
                        isSelected
                          ? "bg-cyan-500/15 hover:bg-cyan-500/20"
                          : "hover:bg-slate-800/40"
                      }`}
                    >
                      {/* Rank Medal */}
                      <td className="py-3.5 px-3 text-center">
                        <span
                          className={`w-7 h-7 rounded-full inline-flex items-center justify-center font-mono font-bold text-xs ${
                            item.rank === 1
                              ? "bg-amber-400 text-slate-950 shadow-md shadow-amber-500/30"
                              : item.rank === 2
                              ? "bg-slate-300 text-slate-950"
                              : item.rank === 3
                              ? "bg-amber-700 text-white"
                              : "bg-slate-900 text-slate-400 border border-slate-800"
                          }`}
                        >
                          {item.rank}
                        </span>
                      </td>

                      {/* Site Name */}
                      <td className="py-3.5 px-4 font-semibold text-white font-mono flex items-center space-x-2">
                        <MapPin className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                        <span className="group-hover:text-cyan-300 transition-colors">{item.site_name}</span>
                        {isSelected && (
                          <span className="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-cyan-400 text-slate-950">
                            SELECTED
                          </span>
                        )}
                      </td>

                      {/* Region & Operation */}
                      <td className="py-3.5 px-4 font-mono text-slate-300">
                        <div>{item.region}</div>
                        <div className="text-[10px] text-slate-500">{item.operation_type}</div>
                      </td>

                      {/* Current SII Score */}
                      <td className="py-3.5 px-4 text-center">
                        <span
                          className={`px-2.5 py-1 rounded-lg font-mono font-bold text-sm border inline-flex items-center space-x-1 ${siiColor}`}
                        >
                          <span>{item.current_sii}</span>
                          <span className="text-[10px] opacity-70">/100</span>
                        </span>
                      </td>

                      {/* Trend Delta */}
                      <td className="py-3.5 px-4 text-center font-mono">
                        <span
                          className={`inline-flex items-center space-x-1 text-xs font-bold ${
                            item.sii_delta > 0
                              ? "text-emerald-400"
                              : item.sii_delta < 0
                              ? "text-red-400"
                              : "text-slate-400"
                          }`}
                        >
                          {item.sii_delta > 0 ? (
                            <ArrowUpRight className="w-3.5 h-3.5" />
                          ) : item.sii_delta < 0 ? (
                            <ArrowDownRight className="w-3.5 h-3.5" />
                          ) : (
                            <Minus className="w-3.5 h-3.5" />
                          )}
                          <span>
                            {item.sii_delta > 0 ? `+${item.sii_delta}` : `${item.sii_delta}`}
                          </span>
                        </span>
                      </td>

                      {/* SIF Density */}
                      <td className="py-3.5 px-4 text-center font-mono">
                        <span className="text-red-400 font-bold">
                          {Math.round(item.sif_density * 100)}%
                        </span>
                        <div className="text-[10px] text-slate-500">
                          {item.sif_reports_count}/{item.total_reports} reps
                        </div>
                      </td>

                      {/* Top Barrier Failure */}
                      <td className="py-3.5 px-4">
                        <span className="inline-block text-[11px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/25 truncate max-w-[200px]">
                          {item.top_barrier_failure || "None"}
                        </span>
                      </td>

                      {/* Status Tier */}
                      <td className="py-3.5 px-4 text-right font-mono">
                        <span
                          className={`px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wider border ${getTierBadge(
                            item.status_tier
                          )}`}
                        >
                          {item.status_tier}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ================= 3. ASSET DEEP-DIVE & TREND CHART ================= */}
      {selectedSite && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* LEFT: 6-Month SII Trend Line Chart (7 Cols) */}
          <div className="lg:col-span-7 bg-[#0c1322]/90 border border-slate-800/90 rounded-xl p-5 shadow-xl backdrop-blur-md space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800/80">
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="text-base font-bold text-white font-mono">
                    {selectedSite.site_name}
                  </h3>
                  <span className="px-2 py-0.2 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700 font-bold">
                    Rank #{selectedSite.rank}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  6-Month Historical Safety Improvement Index & SIF Density Trajectory
                </p>
              </div>

              <div className="text-right">
                <div className="text-xs font-mono text-slate-400">Current Score</div>
                <div className="text-xl font-black font-mono text-cyan-400">
                  {selectedSite.current_sii}
                  <span className="text-xs text-slate-500 font-normal"> / 100</span>
                </div>
              </div>
            </div>

            {/* Line Chart */}
            <div className="h-72 w-full pt-2">
              {isLoadingTrend ? (
                <div className="h-full flex items-center justify-center">
                  <div className="text-xs font-mono text-slate-500 animate-pulse">
                    Loading trend history for {selectedSite.site_name}...
                  </div>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={siteTrend?.trend || []}
                    margin={{ top: 10, right: 20, left: -10, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                    <XAxis
                      dataKey="period"
                      stroke="#94a3b8"
                      fontSize={11}
                      tickLine={false}
                    />
                    <YAxis
                      domain={[40, 100]}
                      stroke="#64748b"
                      fontSize={11}
                      tickLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#090d16",
                        borderColor: "#1e293b",
                        borderRadius: "0.5rem",
                        fontSize: "12px",
                        color: "#f8fafc",
                        fontFamily: "monospace",
                      }}
                      formatter={(val: any, name: any) => [
                        name === "sii_score" ? `${val} pts` : `${Math.round(val * 100)}%`,
                        name === "sii_score" ? "Safety Improvement Index" : "SIF Density",
                      ]}
                    />
                    <Legend
                      verticalAlign="top"
                      align="right"
                      wrapperStyle={{ fontSize: "11px", paddingBottom: "10px" }}
                    />
                    <Line
                      type="monotone"
                      dataKey="sii_score"
                      name="Safety Improvement Index (SII)"
                      stroke="#06b6d4"
                      strokeWidth={3}
                      dot={{ r: 4, fill: "#06b6d4", strokeWidth: 2, stroke: "#090e18" }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="grid grid-cols-3 gap-2 pt-3 border-t border-slate-800/80 text-center text-xs font-mono">
              <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase">Observations</div>
                <div className="text-sm font-bold text-white mt-0.5">{selectedSite.total_reports}</div>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase">SIF Precursors</div>
                <div className="text-sm font-bold text-red-400 mt-0.5">{selectedSite.sif_reports_count}</div>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase">Compromised Barriers</div>
                <div className="text-sm font-bold text-amber-400 mt-0.5">
                  {selectedSite.barrier_breakdown.length} Categories
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT: "What-If" Barrier Recurrence Simulator Panel (5 Cols) */}
          <div className="lg:col-span-5 bg-gradient-to-b from-[#0c1322] to-[#0d1627] border border-slate-800/90 rounded-xl p-5 shadow-xl backdrop-blur-md space-y-4 flex flex-col justify-between">
            <div className="space-y-1 pb-3 border-b border-slate-800/80">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wider flex items-center space-x-2">
                  <Sliders className="w-4 h-4 text-cyan-400" />
                  <span>"What-If" Barrier Simulator</span>
                </h3>
                <span
                  className={`px-2 py-0.2 rounded text-[10px] font-mono font-bold border ${
                    isSimulating
                      ? "bg-amber-500/20 text-amber-300 border-amber-500/40 animate-pulse"
                      : "bg-cyan-500/10 text-cyan-300 border-cyan-500/30"
                  }`}
                >
                  {isSimulating ? "CALCULATING..." : "PROJECTION ENGINE"}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Simulate projected SII score gains by reducing recurrence of specific safety barrier failures:
              </p>
            </div>

            {/* Quick Presets */}
            <div className="flex items-center space-x-2 text-xs font-mono">
              <span className="text-slate-500 text-[11px]">Presets:</span>
              <button
                type="button"
                onClick={() => handleApplyPreset(25)}
                className="px-2 py-0.5 rounded bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition"
              >
                -25%
              </button>
              <button
                type="button"
                onClick={() => handleApplyPreset(50)}
                className="px-2 py-0.5 rounded bg-slate-900 hover:bg-slate-800 text-cyan-300 border border-slate-800 transition font-bold"
              >
                -50%
              </button>
              <button
                type="button"
                onClick={() => handleApplyPreset(75)}
                className="px-2 py-0.5 rounded bg-slate-900 hover:bg-slate-800 text-emerald-300 border border-slate-800 transition font-bold"
              >
                -75%
              </button>
              <button
                type="button"
                onClick={handleResetSliders}
                className="px-2 py-0.5 rounded text-slate-400 hover:text-white underline text-[11px] ml-auto"
              >
                Reset
              </button>
            </div>

            {/* Sliders List for Top Barriers */}
            <div className="space-y-3.5 max-h-56 overflow-y-auto pr-1">
              {selectedSite.barrier_breakdown.length === 0 ? (
                <div className="p-4 text-center text-xs font-mono text-slate-500">
                  No recurring barrier failures registered for this asset.
                </div>
              ) : (
                selectedSite.barrier_breakdown.map((b) => {
                  const currentVal = barrierReductions[b.barrier_type] || 0;
                  return (
                    <div key={b.barrier_type} className="space-y-1.5 font-mono text-xs">
                      <div className="flex items-center justify-between text-slate-300">
                        <span className="truncate max-w-[200px] font-medium">{b.barrier_type}</span>
                        <span className="text-cyan-400 font-bold shrink-0">
                          Reduce by -{currentVal}%
                        </span>
                      </div>

                      <div className="flex items-center space-x-3">
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="5"
                          value={currentVal}
                          onChange={(e) => handleSliderChange(b.barrier_type, Number(e.target.value))}
                          className="w-full accent-cyan-400 h-1.5 bg-slate-950 rounded-lg cursor-pointer"
                        />
                        <span className="text-[10px] text-slate-500 w-12 text-right shrink-0">
                          ({b.failure_count} fails)
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Projected Score Callout Box */}
            <div className="p-4 rounded-xl bg-gradient-to-r from-cyan-950/40 via-slate-950 to-slate-950 border border-cyan-500/40 space-y-2">
              <div className="flex items-center justify-between font-mono">
                <span className="text-xs text-slate-400">Baseline Score:</span>
                <span className="text-sm font-bold text-slate-300">{selectedSite.current_sii}</span>
              </div>

              <div className="flex items-center justify-between font-mono">
                <span className="text-xs text-slate-400">Projected SII Score:</span>
                <div className="flex items-baseline space-x-1.5">
                  <span className="text-xl font-black text-cyan-300">
                    {simulationResult ? simulationResult.projected_sii : selectedSite.current_sii}
                  </span>
                  {simulationResult && simulationResult.sii_gain > 0 && (
                    <span className="text-xs font-bold text-emerald-400">
                      (+{simulationResult.sii_gain} pts)
                    </span>
                  )}
                </div>
              </div>

              {simulationResult && simulationResult.sii_gain > 0 && (
                <div className="pt-2 border-t border-slate-800 text-[11px] font-sans text-slate-300 flex items-start space-x-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />
                  <span>
                    Projected rank improves from <strong>#{selectedSite.rank}</strong> to{" "}
                    <strong className="text-cyan-300">#{simulationResult.projected_rank}</strong> on the asset leaderboard.
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ================= THREE-CARD FEATURE SECTION ================= */}
      <FeatureCardsSection />
    </div>
  );
};
