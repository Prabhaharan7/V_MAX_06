import React, { useState } from "react"
import { Sparkles, CheckCircle2, ShieldAlert, ArrowRight, Zap, Info } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"

interface AnalysisResult {
  is_sif_precursor: boolean
  sif_confidence: number
  precursor_category?: string
  risk_level: string
  ai_analysis_summary: string
  key_risk_factors: string[]
}

const PRESET_SCENARIOS = [
  {
    name: "Well Kick / Blowout Precursor",
    title: "Drilling fluid pit level rise & sudden casing pressure surge on Rig #4",
    description: "During drilling operations at 2,800m depth, the mud logging sensor indicated a 15-barrel pit volume increase. Casing pressure rapidly climbed to 450 psi. Driller initiated soft shut-in on the Annular BOP but noted sluggish choke manifold hydraulic response.",
    location: "Duliajan Rig #4 (Well NH-48)",
    type: "Near Miss",
  },
  {
    name: "Sour Gas (H2S) Precursor",
    title: "Sour gas atmospheric sensor tripped above 15 ppm during separator maintenance",
    description: "Maintenance crew was isolating line near production separator V-102. Fixed H2S detector sounded audible alarm reaching 22 ppm. Workers evacuated immediately; secondary SCBA pack seal showed wear upon inspection.",
    location: "Digboi Production Hub 2",
    type: "Unsafe Condition",
  },
  {
    name: "Suspended Load Rigging Hazard",
    title: "Crane hoist sling frayed during heavy drill collar lift near monkey board",
    description: "While moving an 8-ton drill collar assembly over the active rig floor, spotter observed wire rope strand snapping on the primary bridle. Load swung within 2 meters of the roughneck station before being set down.",
    location: "Moran Field Station 9",
    type: "Near Miss",
  },
  {
    name: "Minor PPE Non-Compliance",
    title: "Worker observed without safety glasses in tool store room",
    description: "During routine morning walkthrough, storekeeper was seen organizing hand tools on low shelves without impact goggles.",
    location: "Central Warehouse Store",
    type: "Unsafe Act",
  }
]

interface ReportAnalyzerProps {
  onReportSubmitted?: () => void
}

export const ReportAnalyzer: React.FC<ReportAnalyzerProps> = ({ onReportSubmitted }) => {
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [location, setLocation] = useState("Duliajan Drilling Rig #4")
  const [reportType, setReportType] = useState("Near Miss")
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [submittedId, setSubmittedId] = useState<string | null>(null)

  const handleApplyPreset = (preset: typeof PRESET_SCENARIOS[0]) => {
    setTitle(preset.title)
    setDescription(preset.description)
    setLocation(preset.location)
    setReportType(preset.type)
    setResult(null)
    setSubmittedId(null)
  }

  const handleAnalyze = async (saveToDb: boolean = false) => {
    if (!title.trim() || !description.trim()) return
    setLoading(true)
    setSubmittedId(null)
    try {
      const endpoint = saveToDb ? "/api/v1/reports" : "/api/v1/analyze"
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          description,
          location,
          report_type: reportType,
          reported_by: "Field Safety Supervisor",
        }),
      })

      if (!res.ok) throw new Error("API request failed")
      const data = await res.json()

      if (saveToDb) {
        setResult({
          is_sif_precursor: data.is_sif_precursor,
          sif_confidence: data.sif_confidence,
          precursor_category: data.precursor_category,
          risk_level: data.risk_level,
          ai_analysis_summary: data.ai_analysis_summary,
          key_risk_factors: [],
        })
        setSubmittedId(data.id)
        if (onReportSubmitted) onReportSubmitted()
      } else {
        setResult(data)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Form Input Column */}
      <div className="lg:col-span-7 space-y-4">
        <Card className="glass-card border-slate-800">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xl text-slate-100 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-amber-400" />
                Safety Incident NLP Evaluator
              </CardTitle>
              <Badge variant="outline" className="border-amber-500/30 text-amber-300 bg-amber-500/10 font-mono text-[11px]">
                High-Energy Precursor Detector
              </Badge>
            </div>
            <CardDescription className="text-slate-400">
              Submit or test safety observation narratives to instantly identify Serious Injury & Fatality (SIF) precursors.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            {/* Presets */}
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                Quick Test Scenarios (Oil & Gas E&P)
              </label>
              <div className="grid grid-cols-2 gap-2">
                {PRESET_SCENARIOS.map((preset, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleApplyPreset(preset)}
                    className="text-left p-2.5 rounded border border-slate-800 bg-slate-900/60 hover:bg-slate-800 hover:border-amber-500/40 transition-all text-xs group"
                  >
                    <div className="font-semibold text-slate-200 group-hover:text-amber-400 truncate">
                      {preset.name}
                    </div>
                    <div className="text-[11px] text-slate-500 truncate mt-0.5">
                      {preset.type} • {preset.location}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Input fields */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-300 font-medium block mb-1">Observation Title</label>
                <Input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Wellhead pressure relief valve chatter"
                  className="bg-slate-950/60 border-slate-800 focus:border-amber-500/60"
                />
              </div>
              <div>
                <label className="text-xs text-slate-300 font-medium block mb-1">Location / Asset</label>
                <Input
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="e.g. Duliajan Rig #4"
                  className="bg-slate-950/60 border-slate-800 focus:border-amber-500/60"
                />
              </div>
            </div>

            <div>
              <label className="text-xs text-slate-300 font-medium block mb-1">
                Detailed Incident / Near-Miss Narrative
              </label>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
                placeholder="Describe exact physical conditions, equipment behavior, energy sources, pressure spikes, gas detection, or personnel positioning..."
                className="bg-slate-950/60 border-slate-800 focus:border-amber-500/60"
              />
            </div>
          </CardContent>

          <CardFooter className="flex items-center justify-between pt-2 border-t border-slate-800/60">
            <Button
              variant="outline"
              size="sm"
              disabled={loading || !title.trim() || !description.trim()}
              onClick={() => handleAnalyze(false)}
              className="border-slate-700 hover:border-cyan-500/50 hover:bg-slate-800 text-cyan-300"
            >
              <Zap className="w-3.5 h-3.5 mr-1.5 text-cyan-400" />
              Live NLP Preview
            </Button>

            <Button
              variant="oil"
              size="sm"
              disabled={loading || !title.trim() || !description.trim()}
              onClick={() => handleAnalyze(true)}
              className="gap-2 shadow-amber-500/20"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{loading ? "Processing..." : "Submit & Store in pgvector"}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </CardFooter>
        </Card>
      </div>

      {/* Analysis Result Column */}
      <div className="lg:col-span-5">
        <Card className={`glass-card border-slate-800 h-full flex flex-col ${result?.is_sif_precursor ? "border-amber-500/50 glow-amber" : ""}`}>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg text-slate-200 flex items-center justify-between">
              <span>AI Precursor Classification</span>
              {result && (
                <Badge
                  variant={
                    result.risk_level === "Critical"
                      ? "critical"
                      : result.risk_level === "High"
                      ? "destructive"
                      : result.risk_level === "Medium"
                      ? "warning"
                      : "success"
                  }
                >
                  {result.risk_level} Risk
                </Badge>
              )}
            </CardTitle>
          </CardHeader>

          <CardContent className="flex-1 flex flex-col justify-center">
            {!result ? (
              <div className="text-center py-12 px-4 border border-dashed border-slate-800 rounded-lg">
                <Info className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-sm font-medium text-slate-400">No report analyzed yet</p>
                <p className="text-xs text-slate-500 max-w-xs mx-auto mt-1">
                  Select a preset test scenario or input an incident description to evaluate SIF precursor signals.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* SIF Status Banner */}
                <div
                  className={`p-4 rounded-lg border ${
                    result.is_sif_precursor
                      ? "bg-rose-950/40 border-rose-800/80 text-rose-200"
                      : "bg-emerald-950/30 border-emerald-800/60 text-emerald-200"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {result.is_sif_precursor ? (
                      <ShieldAlert className="w-6 h-6 text-rose-400 shrink-0 mt-0.5" />
                    ) : (
                      <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0 mt-0.5" />
                    )}
                    <div>
                      <div className="font-bold text-sm tracking-wide">
                        {result.is_sif_precursor
                          ? "CRITICAL SIF PRECURSOR DETECTED"
                          : "ROUTINE SAFETY OBSERVATION"}
                      </div>
                      <div className="text-xs opacity-90 mt-1 font-mono">
                        Model Confidence: {(result.sif_confidence * 100).toFixed(0)}%
                        {result.precursor_category && ` • Category: ${result.precursor_category}`}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Explanation */}
                <div className="p-3.5 rounded-md bg-slate-950/60 border border-slate-800">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    AI Semantic Evaluation
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {result.ai_analysis_summary}
                  </p>
                </div>

                {submittedId && (
                  <div className="p-2.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center justify-between font-mono">
                    <span>Saved to pgvector database</span>
                    <span className="text-[10px] text-slate-400 truncate max-w-[120px]">{submittedId}</span>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
