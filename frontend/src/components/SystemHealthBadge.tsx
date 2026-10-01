import React, { useEffect, useState } from "react"
import { Activity, CheckCircle2, AlertTriangle, RefreshCw } from "lucide-react"
import { Badge } from "@/components/ui/badge"

interface HealthData {
  status: string
  app_name: string
  version: string
  timestamp: string
  database: string
  environment: string
}

export const SystemHealthBadge: React.FC = () => {
  const [health, setHealth] = useState<HealthData | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<boolean>(false)

  const checkHealth = async () => {
    setLoading(true)
    try {
      const res = await fetch("/api/health")
      if (!res.ok) throw new Error("Health check failed")
      const data: HealthData = await res.json()
      setHealth(data)
      setError(false)
    } catch {
      setError(true)
      setHealth(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 15000)
    return () => clearInterval(interval)
  }, [])

  if (loading && !health) {
    return (
      <Badge variant="outline" className="flex items-center gap-1.5 py-1 px-3 bg-slate-800/60 border-slate-700 text-slate-300">
        <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-400" />
        <span className="text-xs">Checking Engine...</span>
      </Badge>
    )
  }

  if (error || !health || health.status !== "ok") {
    return (
      <Badge variant="destructive" className="flex items-center gap-1.5 py-1 px-3 bg-rose-950/60 border border-rose-800 text-rose-300 cursor-pointer" onClick={checkHealth}>
        <AlertTriangle className="w-3.5 h-3.5 text-rose-400 animate-bounce" />
        <span className="text-xs font-mono">Backend: Degraded / Offline</span>
      </Badge>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <Badge variant="success" className="flex items-center gap-1.5 py-1 px-3 bg-emerald-950/60 border border-emerald-800 text-emerald-300 font-mono text-xs">
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
        <span>FastAPI + pgvector Online</span>
      </Badge>
      <Badge variant="outline" className="hidden sm:flex items-center gap-1 py-1 px-2 text-[10px] text-slate-400 border-slate-700 bg-slate-900/40 font-mono">
        <Activity className="w-3 h-3 text-cyan-400" />
        <span>DB: {health.database}</span>
      </Badge>
    </div>
  )
}
