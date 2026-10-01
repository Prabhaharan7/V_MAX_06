import React from "react"
import { ShieldAlert, Cpu, ExternalLink } from "lucide-react"
import { SystemHealthBadge } from "@/components/SystemHealthBadge"

export const Header: React.FC = () => {
  return (
    <header className="sticky top-0 z-50 border-b border-border/80 bg-background/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand & Logo */}
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-gradient-to-br from-amber-500/20 to-cyan-500/20 border border-amber-500/30 flex items-center justify-center">
              <ShieldAlert className="w-6 h-6 text-amber-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold tracking-tight text-lg text-white">
                  SIF Sentinel <span className="text-amber-400">AI</span>
                </span>
                <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  SIH 2026 PS 26165
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">
                Serious Injury & Fatality Precursor Intelligence • Oil India
              </p>
            </div>
          </div>

          {/* Right Action Items */}
          <div className="flex items-center gap-3">
            <SystemHealthBadge />
            <a
              href="/docs"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-300 hover:text-white px-3 py-1.5 rounded-md border border-slate-700 bg-slate-900/60 hover:bg-slate-800 transition-colors"
            >
              <Cpu className="w-3.5 h-3.5 text-cyan-400" />
              <span>API Swagger</span>
              <ExternalLink className="w-3 h-3 text-slate-400" />
            </a>
          </div>
        </div>
      </div>
    </header>
  )
}
