import React, { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  ShieldAlert,
  ShieldCheck,
  Flame,
  CheckCircle2,
  Clock,
  MapPin,
  RefreshCw,
  Search,
  Check,
  ExternalLink,
  Bell,
  Radio,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

// ==============================================================================
// Types & Interfaces
// ==============================================================================

interface AlertItem {
  id: number;
  report_id?: number | null;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | string;
  title: string;
  site_name: string;
  region: string;
  operation_type: string;
  timestamp: string;
  time_ago?: string | null;
  description: string;
  lsr_category: string;
  compromised_barrier?: string | null;
  alert_type: string;
  sent_to: string;
  acknowledged: boolean;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
}

interface AlertStats {
  total_active_alerts: number;
  unacknowledged_count: number;
  critical_count: number;
  high_count: number;
  last_triggered_at?: string | null;
}

// ==============================================================================
// Main Alerts Page Component
// ==============================================================================

export const AlertsPage: React.FC = () => {
  const { token } = useAuth();

  // State Management
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [acknowledgingIds, setAcknowledgingIds] = useState<Set<number>>(new Set());

  // Filter & Search
  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [unackOnly, setUnackOnly] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // 1. Fetch Alerts Feed
  const fetchAlerts = async () => {
    setIsLoading(true);
    try {
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const [alertsRes, statsRes] = await Promise.all([
        fetch(`/api/alerts?unacknowledged_only=${unackOnly}`, { headers }),
        fetch("/api/alerts/stats", { headers }),
      ]);

      if (alertsRes.ok) {
        const data: AlertItem[] = await alertsRes.json();
        setAlerts(data);
      }

      if (statsRes.ok) {
        const sData: AlertStats = await statsRes.json();
        setStats(sData);
      }
    } catch (e) {
      console.error("Error fetching alerts feed:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [unackOnly, token]);

  // 2. Acknowledge Alert Handler
  const handleAcknowledge = async (alertId: number, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setAcknowledgingIds((prev) => new Set(prev).add(alertId));

    try {
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`/api/alerts/${alertId}/acknowledge`, {
        method: "POST",
        headers,
      });

      if (res.ok) {
        // Optimistically update local state
        setAlerts((prev) =>
          prev.map((a) =>
            a.id === alertId
              ? {
                  ...a,
                  acknowledged: true,
                  acknowledged_at: new Date().toISOString(),
                  acknowledged_by: "HSE Supervisor",
                }
              : a
          )
        );

        setToastMessage(`Alert #${alertId} acknowledged successfully.`);
        setTimeout(() => setToastMessage(null), 3000);

        // Update stats
        setStats((prev) =>
          prev ? { ...prev, unacknowledged_count: Math.max(0, prev.unacknowledged_count - 1) } : null
        );
      }
    } catch (err) {
      console.error("Error acknowledging alert:", err);
    } finally {
      setAcknowledgingIds((prev) => {
        const next = new Set(prev);
        next.delete(alertId);
        return next;
      });
    }
  };

  // Filtered Alerts List
  const filteredAlerts = useMemo(() => {
    return alerts.filter((alert) => {
      const matchesSearch =
        !searchQuery ||
        alert.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        alert.site_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        alert.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        alert.lsr_category.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesSeverity =
        severityFilter === "all" || alert.severity.toUpperCase() === severityFilter.toUpperCase();

      return matchesSearch && matchesSeverity;
    });
  }, [alerts, searchQuery, severityFilter]);

  const unackedCount = alerts.filter((a) => !a.acknowledged).length;

  return (
    <div className="space-y-6 pb-16">
      {/* ================= 1. HEADER & SUMMARY METRICS ================= */}
      <div className="border-b border-slate-800/80 pb-3 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-2xl font-black tracking-tight text-white flex items-center space-x-2">
              <span>Precursor & Hazard Spike Alerts</span>
            </h1>
            <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-red-500/20 text-red-300 border border-red-500/40 rounded flex items-center space-x-1">
              <Radio className="w-3 h-3 animate-pulse text-red-400" />
              <span>EARLY WARNING FEED</span>
            </span>
          </div>
          <p className="text-xs text-slate-400 font-normal mt-0.5">
            Proactive automated push notifications triggered when asset barrier failure frequencies breach safety thresholds
          </p>
        </div>

        <button
          onClick={fetchAlerts}
          className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs font-mono font-bold transition flex items-center space-x-1.5 shrink-0"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Alerts</span>
        </button>
      </div>

      {/* Toast Notification Banner */}
      {toastMessage && (
        <div className="p-3 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-xs font-mono text-emerald-300 flex items-center space-x-2 animate-in fade-in duration-200">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Summary KPI Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-xl bg-[#0c1322]/90 border border-red-500/30 shadow-lg shadow-red-950/20 flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-red-500/20 text-red-400 border border-red-500/40 flex items-center justify-center shrink-0 animate-pulse">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[10px] font-mono text-slate-400 uppercase">Unacknowledged</div>
            <div className="text-xl font-black font-mono text-red-400 mt-0.5">
              {unackedCount}
              <span className="text-xs text-slate-500 font-normal"> / {alerts.length}</span>
            </div>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0c1322]/90 border border-slate-800 flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-orange-500/15 text-orange-400 border border-orange-500/30 flex items-center justify-center shrink-0">
            <Flame className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[10px] font-mono text-slate-400 uppercase">Critical Spikes</div>
            <div className="text-xl font-black font-mono text-orange-400 mt-0.5">
              {stats?.critical_count || 2}
            </div>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0c1322]/90 border border-slate-800 flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 flex items-center justify-center shrink-0">
            <Bell className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[10px] font-mono text-slate-400 uppercase">Active Feeds</div>
            <div className="text-xl font-black font-mono text-cyan-300 mt-0.5">
              {alerts.length}
            </div>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0c1322]/90 border border-slate-800 flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center justify-center shrink-0">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[10px] font-mono text-slate-400 uppercase">Acknowledged</div>
            <div className="text-xl font-black font-mono text-emerald-400 mt-0.5">
              {alerts.length - unackedCount}
            </div>
          </div>
        </div>
      </div>

      {/* ================= 2. SEARCH & FILTER TOOLBAR ================= */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-xl bg-[#0c1322]/80 border border-slate-800 text-xs font-mono">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search alerts by asset, rule, or description..."
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 outline-none focus:border-red-500/60"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Unacknowledged Toggle */}
          <button
            onClick={() => setUnackOnly(!unackOnly)}
            className={`px-3 py-1.5 rounded-lg font-bold transition border flex items-center space-x-1.5 ${
              unackOnly
                ? "bg-red-500 text-white border-red-500 shadow-md shadow-red-950/40"
                : "bg-slate-950 text-slate-400 hover:text-white border-slate-800"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-red-400 animate-pulse" />
            <span>Unacknowledged Only ({unackedCount})</span>
          </button>

          {/* Severity Filters */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="py-1.5 px-2.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 outline-none focus:border-red-500/60"
          >
            <option value="all">All Severities</option>
            <option value="CRITICAL">Critical Only</option>
            <option value="HIGH">High Only</option>
            <option value="MEDIUM">Medium Only</option>
          </select>
        </div>
      </div>

      {/* ================= 3. ALERTS FEED ================= */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3 animate-pulse h-32"
            >
              <div className="h-4 w-48 bg-slate-800 rounded" />
              <div className="h-4 w-full bg-slate-800 rounded" />
            </div>
          ))}
        </div>
      ) : filteredAlerts.length === 0 ? (
        <div className="p-12 rounded-xl bg-[#0c1322]/80 border border-slate-800 text-center space-y-3">
          <ShieldCheck className="w-10 h-10 text-emerald-400 mx-auto" />
          <div className="text-base font-bold text-white font-mono">No Alerts Pending Review</div>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            {unackOnly
              ? "All high-severity early warning alerts have been acknowledged by safety supervisors."
              : "No active hazard alerts matched your query."}
          </p>
        </div>
      ) : (
        <div className="space-y-3.5">
          {filteredAlerts.map((alert) => {
            const isUnack = !alert.acknowledged;
            const isCritical = alert.severity === "CRITICAL";

            return (
              <div
                key={alert.id}
                className={`p-5 rounded-xl border backdrop-blur-md transition-all duration-200 relative overflow-hidden shadow-lg ${
                  isUnack
                    ? "border-l-[5px] border-l-red-500 border-slate-800 bg-gradient-to-r from-red-950/25 via-[#0c1322] to-[#0c1322] shadow-red-950/20"
                    : "border-l-[5px] border-l-slate-700 border-slate-800/80 bg-[#0c1322]/60 opacity-85"
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="space-y-2 flex-1">
                    {/* Badge Row */}
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                          isCritical
                            ? "bg-red-500/25 text-red-300 border-red-500/50 animate-pulse"
                            : alert.severity === "HIGH"
                            ? "bg-orange-500/20 text-orange-300 border-orange-500/40"
                            : "bg-amber-500/20 text-amber-300 border-amber-500/40"
                        }`}
                      >
                        {alert.severity} PRIORITY
                      </span>

                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-900 text-cyan-300 border border-slate-800">
                        {alert.lsr_category}
                      </span>

                      <span className="text-xs font-mono font-bold text-slate-300 flex items-center space-x-1">
                        <MapPin className="w-3.5 h-3.5 text-amber-400" />
                        <span>{alert.site_name}</span>
                      </span>

                      <div className="flex items-center space-x-1 text-xs font-mono text-slate-400 ml-auto sm:ml-0">
                        <Clock className="w-3.5 h-3.5" />
                        <span>{alert.time_ago || new Date(alert.timestamp).toLocaleTimeString()}</span>
                      </div>
                    </div>

                    {/* Headline Title */}
                    <h3 className="text-base font-bold text-white leading-snug">{alert.title}</h3>

                    {/* Description Narrative */}
                    <p className="text-xs text-slate-300 leading-relaxed font-sans">{alert.description}</p>

                    {/* Compromised Barrier Info */}
                    {alert.compromised_barrier && (
                      <div className="text-[11px] font-mono text-slate-400 pt-1 flex items-center space-x-2">
                        <span className="text-slate-500 uppercase text-[10px]">Compromised Barrier:</span>
                        <span className="text-amber-300 font-semibold">{alert.compromised_barrier}</span>
                      </div>
                    )}
                  </div>

                  {/* Actions Column */}
                  <div className="flex flex-col sm:items-end justify-between space-y-2 shrink-0 pt-2 sm:pt-0">
                    {isUnack ? (
                      <button
                        disabled={acknowledgingIds.has(alert.id)}
                        onClick={(e) => handleAcknowledge(alert.id, e)}
                        className="py-2 px-4 rounded-lg bg-red-500 hover:bg-red-600 text-white font-mono text-xs font-bold transition shadow-lg shadow-red-950/50 flex items-center justify-center space-x-1.5 disabled:opacity-50"
                      >
                        {acknowledgingIds.has(alert.id) ? (
                          <span>Saving...</span>
                        ) : (
                          <>
                            <Check className="w-4 h-4" />
                            <span>Acknowledge Alert</span>
                          </>
                        )}
                      </button>
                    ) : (
                      <span className="px-3 py-1.5 rounded-lg bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-xs font-mono font-bold flex items-center space-x-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Acknowledged</span>
                      </span>
                    )}

                    {alert.report_id && (
                      <Link
                        to={`/reports/${alert.report_id}`}
                        className="text-xs font-mono text-cyan-400 hover:text-cyan-300 flex items-center space-x-1 pt-1"
                      >
                        <span>Inspect Observation #{alert.report_id}</span>
                        <ExternalLink className="w-3.5 h-3.5" />
                      </Link>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
