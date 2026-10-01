import React, { useEffect, useState } from "react"
import { AlertTriangle, TrendingUp, ShieldCheck, Flame, Layers, Clock, MapPin } from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface SafetyStats {
  total_reports: number
  sif_precursors_detected: number
  high_critical_risk_count: number
  sif_percentage: number
}

interface SafetyReport {
  id: string
  title: string
  description: string
  location: string
  report_type: string
  is_sif_precursor: boolean
  sif_confidence: number
  precursor_category?: string
  risk_level: string
  ai_analysis_summary?: string
  created_at: string
}

export const PrecursorDashboard: React.FC<{ refreshTrigger: number }> = ({ refreshTrigger }) => {
  const [stats, setStats] = useState<SafetyStats | null>(null)
  const [reports, setReports] = useState<SafetyReport[]>([])
  const [filterSif, setFilterSif] = useState<boolean | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      // Fetch stats
      const statsRes = await fetch("/api/v1/stats")
      if (statsRes.ok) {
        const statsData = await statsRes.json()
        setStats(statsData)
      }

      // Fetch reports
      const filterQuery = filterSif !== null ? `&sif_only=${filterSif}` : ""
      const reportsRes = await fetch(`/api/v1/reports?limit=20${filterQuery}`)
      if (reportsRes.ok) {
        const reportsData = await reportsRes.json()
        setReports(reportsData)
      }
    } catch (err) {
      console.error("Failed to load dashboard data:", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [refreshTrigger, filterSif])

  return (
    <div className="space-y-6">
      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="glass-card border-slate-800">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Total Reports</p>
              <h4 className="text-2xl font-bold text-white mt-1">{stats?.total_reports ?? 0}</h4>
              <p className="text-[11px] text-slate-500 mt-0.5">Safety logs processed</p>
            </div>
            <div className="p-3 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <Layers className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card border-slate-800 border-l-4 border-l-rose-500">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">SIF Precursors</p>
              <h4 className="text-2xl font-bold text-rose-400 mt-1">{stats?.sif_precursors_detected ?? 0}</h4>
              <p className="text-[11px] text-rose-300/70 mt-0.5">{stats?.sif_percentage ?? 0}% of all observations</p>
            </div>
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card border-slate-800 border-l-4 border-l-amber-500">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">High / Critical Risk</p>
              <h4 className="text-2xl font-bold text-amber-400 mt-1">{stats?.high_critical_risk_count ?? 0}</h4>
              <p className="text-[11px] text-slate-500 mt-0.5">Immediate barrier attention</p>
            </div>
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400">
              <Flame className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card border-slate-800">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Vector Embeddings</p>
              <h4 className="text-2xl font-bold text-emerald-400 mt-1">pgvector</h4>
              <p className="text-[11px] text-emerald-300/70 mt-0.5">384-dim semantic index</p>
            </div>
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Safety Feed */}
      <Card className="glass-card border-slate-800">
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-lg text-slate-100 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-amber-400" />
              Precursor Intelligence Feed
            </CardTitle>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilterSif(null)}
              className={`px-2.5 py-1 text-xs rounded font-medium transition-colors ${
                filterSif === null ? "bg-slate-700 text-white" : "bg-slate-900/60 text-slate-400 hover:text-white"
              }`}
            >
              All Reports
            </button>
            <button
              onClick={() => setFilterSif(true)}
              className={`px-2.5 py-1 text-xs rounded font-medium transition-colors ${
                filterSif === true ? "bg-rose-900/80 text-rose-200 border border-rose-700" : "bg-slate-900/60 text-slate-400 hover:text-rose-300"
              }`}
            >
              SIF Precursors Only
            </button>
          </div>
        </CardHeader>

        <CardContent>
          {loading ? (
            <div className="py-8 text-center text-xs text-slate-400">Loading safety records...</div>
          ) : reports.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs">
              No reports stored yet. Use the evaluator above to analyze and store reports.
            </div>
          ) : (
            <div className="space-y-3">
              {reports.map((report) => (
                <div
                  key={report.id}
                  className={`p-4 rounded-lg border transition-all ${
                    report.is_sif_precursor
                      ? "bg-slate-900/80 border-rose-900/50 hover:border-rose-700/80"
                      : "bg-slate-950/40 border-slate-800/80 hover:border-slate-700"
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={
                          report.risk_level === "Critical"
                            ? "critical"
                            : report.risk_level === "High"
                            ? "destructive"
                            : report.risk_level === "Medium"
                            ? "warning"
                            : "success"
                        }
                      >
                        {report.risk_level} Risk
                      </Badge>
                      {report.is_sif_precursor && (
                        <Badge variant="warning" className="text-[10px]">
                          SIF Precursor ({Math.round(report.sif_confidence * 100)}%)
                        </Badge>
                      )}
                      <span className="text-xs text-slate-400 font-medium">{report.report_type}</span>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3 h-3 text-slate-400" />
                        {report.location}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-400" />
                        {new Date(report.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>

                  <h5 className="text-sm font-semibold text-slate-200 mb-1">{report.title}</h5>
                  <p className="text-xs text-slate-400 line-clamp-2">{report.description}</p>

                  {report.precursor_category && (
                    <div className="mt-2.5 pt-2 border-t border-slate-800/60 flex items-center gap-2 text-xs text-amber-300 font-mono">
                      <span className="text-slate-500">Precursor Focus:</span>
                      <span className="bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                        {report.precursor_category}
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
