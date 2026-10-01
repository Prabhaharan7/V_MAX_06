import React, { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Circle,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Sparkles,
  MapPin,
  Compass,
  ChevronRight,
  Radio,
  Layers,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

// ==============================================================================
// Types & Interfaces
// ==============================================================================

interface HeatmapForecastPoint {
  site_id: number;
  site_name: string;
  region: string;
  operation_type: string;
  location_lat: number;
  location_lng: number;
  current_density: number;
  forecast_density: number;
  forecast_trend: "rising" | "stable" | "falling" | string;
  risk_level: "CRITICAL" | "HIGH" | "MODERATE" | "LOW" | string;
  sii_score: number;
  top_risk_factor: string;
  active_precursors_30d: number;
  predicted_breaches_next_30d: number;
  risk_radius_meters: number;
}

// Region Zoom Presets
const REGION_PRESETS = [
  { name: "All India Overview", center: [23.5, 83.5] as [number, number], zoom: 5 },
  { name: "Assam Asset (Upper Assam)", center: [27.35, 95.15] as [number, number], zoom: 9 },
  { name: "Rajasthan Basin (Barmer/Jaisalmer)", center: [26.4, 71.5] as [number, number], zoom: 8 },
  { name: "KG Basin Offshore (Kakinada)", center: [16.95, 82.25] as [number, number], zoom: 9 },
];

// Helper Component to control map view transitions
function ChangeMapView({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, zoom, { duration: 1.2 });
  }, [center, zoom, map]);
  return null;
}

// ==============================================================================
// Custom Leaflet Pulsing DivIcon Generator
// ==============================================================================

function createPulsingMarkerIcon(density: number, riskLevel: string) {
  // Sizing based on forecast density
  const size = Math.max(22, Math.min(48, Math.round(density * 75)));
  const pulseSize = size * 2.2;

  let color = "#10b981"; // Emerald (Low)
  let glowColor = "rgba(16, 185, 129, 0.4)";

  if (riskLevel === "CRITICAL" || density >= 0.35) {
    color = "#ef4444"; // Red
    glowColor = "rgba(239, 68, 68, 0.5)";
  } else if (riskLevel === "HIGH" || density >= 0.22) {
    color = "#f97316"; // Orange
    glowColor = "rgba(249, 115, 22, 0.5)";
  } else if (riskLevel === "MODERATE" || density >= 0.12) {
    color = "#f59e0b"; // Amber
    glowColor = "rgba(245, 158, 11, 0.5)";
  }

  const html = `
    <div style="position: relative; width: ${size}px; height: ${size}px; display: flex; align-items: center; justify-content: center;">
      <!-- Pulsing Outer Ripple -->
      <div style="
        position: absolute;
        width: ${pulseSize}px;
        height: ${pulseSize}px;
        border-radius: 50%;
        background-color: ${glowColor};
        animation: pulse-ring 2.2s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
        pointer-events: none;
      "></div>

      <!-- Core Dot -->
      <div style="
        position: relative;
        width: ${size}px;
        height: ${size}px;
        border-radius: 50%;
        background: radial-gradient(circle at 35% 35%, #ffffff 0%, ${color} 65%, #000000 100%);
        border: 2px solid #ffffff;
        box-shadow: 0 0 14px ${color}, 0 2px 8px rgba(0,0,0,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #ffffff;
        font-family: monospace;
        font-weight: 900;
        font-size: ${size > 32 ? "12px" : "10px"};
      ">
        ${Math.round(density * 100)}%
      </div>
    </div>
  `;

  return L.divIcon({
    html,
    className: "custom-pulsing-marker",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

// ==============================================================================
// Main Risk Map Page Component
// ==============================================================================

export const RiskMapPage: React.FC = () => {
  const { token } = useAuth();

  // State Management
  const [forecastPoints, setForecastPoints] = useState<HeatmapForecastPoint[]>([]);
  const [selectedPoint, setSelectedPoint] = useState<HeatmapForecastPoint | null>(null);
  const [viewMode, setViewMode] = useState<"current" | "forecast">("forecast");
  const [selectedPreset, setSelectedPreset] = useState(REGION_PRESETS[0]);
  const [isLoading, setIsLoading] = useState(true);
  const [showRadiusRings, setShowRadiusRings] = useState(true);

  // Fetch forecast heatmap telemetry
  const fetchHeatmapData = async () => {
    setIsLoading(true);
    try {
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch("/api/forecast/heatmap", { headers });
      if (res.ok) {
        const data: HeatmapForecastPoint[] = await res.json();
        setForecastPoints(data);
        if (data.length > 0 && !selectedPoint) {
          setSelectedPoint(data[0]);
        }
      }
    } catch (e) {
      console.error("Error fetching forecast heatmap:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHeatmapData();
  }, [token]);

  // Telemetry Aggregates
  const stats = useMemo(() => {
    const total = forecastPoints.length;
    const critical = forecastPoints.filter((p) => p.risk_level === "CRITICAL").length;
    const high = forecastPoints.filter((p) => p.risk_level === "HIGH").length;
    const avgForecastDensity =
      total > 0
        ? Math.round(
            (forecastPoints.reduce((acc, p) => acc + p.forecast_density, 0) / total) * 100
          )
        : 0;

    return { total, critical, high, avgForecastDensity };
  }, [forecastPoints]);

  return (
    <div className="space-y-4 pb-12 relative flex flex-col h-[calc(100vh-6rem)] min-h-[640px]">
      {/* CSS Animation Keyframes for Pulsing Ripple */}
      <style>
        {`
          @keyframes pulse-ring {
            0% {
              transform: scale(0.6);
              opacity: 0.8;
            }
            80%, 100% {
              transform: scale(2.2);
              opacity: 0;
            }
          }
          .leaflet-container {
            background: #070b14 !important;
            font-family: inherit;
          }
          .custom-leaflet-popup .leaflet-popup-content-wrapper {
            background: #090e18 !important;
            color: #f8fafc !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 0.75rem !important;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.7) !important;
            padding: 0 !important;
          }
          .custom-leaflet-popup .leaflet-popup-tip {
            background: #090e18 !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
          }
          .custom-leaflet-popup .leaflet-popup-content {
            margin: 0 !important;
            line-height: inherit !important;
          }
        `}
      </style>

      {/* ================= 1. HEADER & VIEW TOGGLES ================= */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-2xl font-black tracking-tight text-white flex items-center space-x-2">
              <span>Geospatial Risk Map & Predictive Heatmap</span>
            </h1>
            <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-red-500/20 text-red-300 border border-red-500/40 rounded flex items-center space-x-1">
              <Radio className="w-3 h-3 animate-pulse text-red-400" />
              <span>LIVE TELEMETRY</span>
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time SIF precursor risk density and 30-day predictive hazard projections across Oil India assets
          </p>
        </div>

        {/* View Mode Toggle Button */}
        <div className="flex items-center space-x-2">
          <div className="p-1 rounded-xl bg-slate-950 border border-slate-800 flex items-center space-x-1 text-xs font-mono">
            <button
              onClick={() => setViewMode("current")}
              className={`px-3 py-1.5 rounded-lg transition font-bold flex items-center space-x-1.5 ${
                viewMode === "current"
                  ? "bg-amber-500 text-slate-950 shadow-md"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <span>Current Observation Density</span>
            </button>

            <button
              onClick={() => setViewMode("forecast")}
              className={`px-3 py-1.5 rounded-lg transition font-bold flex items-center space-x-1.5 ${
                viewMode === "forecast"
                  ? "bg-gradient-to-r from-red-600 to-amber-500 text-white shadow-md shadow-red-950/40"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>30-Day Predictive Forecast</span>
            </button>
          </div>

          <button
            onClick={fetchHeatmapData}
            disabled={isLoading}
            className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition"
            title="Refresh Map Telemetry"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin text-cyan-400" : ""}`} />
          </button>
        </div>
      </div>

      {/* ================= 2. TELEMETRY PILLS & REGION PRESETS ================= */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-[#0c1322]/90 border border-slate-800 text-xs font-mono shrink-0">
        {/* Region View Presets */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-slate-500 text-[11px] flex items-center space-x-1 mr-1">
            <Compass className="w-3.5 h-3.5 text-cyan-400" />
            <span>Region Focus:</span>
          </span>

          {REGION_PRESETS.map((preset) => (
            <button
              key={preset.name}
              onClick={() => setSelectedPreset(preset)}
              className={`px-2.5 py-1 rounded-lg transition border ${
                selectedPreset.name === preset.name
                  ? "bg-cyan-500/20 text-cyan-300 border-cyan-400 font-bold"
                  : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
              }`}
            >
              {preset.name}
            </button>
          ))}
        </div>

        {/* Telemetry Stats */}
        <div className="flex items-center space-x-3 text-slate-300">
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-red-400 font-bold">{stats.critical} Critical Hotspots</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-orange-400" />
            <span className="text-orange-300 font-bold">{stats.high} High Risk</span>
          </div>
          <div className="text-slate-500 hidden sm:inline">|</div>
          <div className="text-slate-400 hidden sm:inline">
            Avg 30d Projection: <strong className="text-amber-400">{stats.avgForecastDensity}%</strong>
          </div>
        </div>
      </div>

      {/* ================= 3. LEAFLET MAP CONTAINER ================= */}
      <div className="flex-1 rounded-xl border border-slate-800/90 overflow-hidden relative shadow-2xl backdrop-blur-md flex">
        <MapContainer
          center={selectedPreset.center}
          zoom={selectedPreset.zoom}
          scrollWheelZoom={true}
          className="w-full h-full z-10"
        >
          <ChangeMapView center={selectedPreset.center} zoom={selectedPreset.zoom} />

          {/* CartoDB Dark Matter Base Tiles */}
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CartoDB</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            maxZoom={18}
          />

          {/* Render Markers & Hazard Radius Circles */}
          {forecastPoints.map((point) => {
            const density = viewMode === "forecast" ? point.forecast_density : point.current_density;
            const markerIcon = createPulsingMarkerIcon(density, point.risk_level);

            const circleColor =
              point.risk_level === "CRITICAL"
                ? "#ef4444"
                : point.risk_level === "HIGH"
                ? "#f97316"
                : point.risk_level === "MODERATE"
                ? "#f59e0b"
                : "#10b981";

            return (
              <React.Fragment key={point.site_id}>
                {/* Hazard Impact Radius Ring */}
                {showRadiusRings && (
                  <Circle
                    center={[point.location_lat, point.location_lng]}
                    radius={point.risk_radius_meters}
                    pathOptions={{
                      color: circleColor,
                      fillColor: circleColor,
                      fillOpacity: density >= 0.35 ? 0.22 : 0.12,
                      weight: 1.5,
                      dashArray: "4, 6",
                    }}
                  />
                )}

                {/* Pulsing Marker */}
                <Marker
                  position={[point.location_lat, point.location_lng]}
                  icon={markerIcon}
                  eventHandlers={{
                    click: () => setSelectedPoint(point),
                  }}
                >
                  <Popup className="custom-leaflet-popup" minWidth={260}>
                    <div className="p-4 space-y-3 font-sans">
                      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                        <span
                          className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                            point.risk_level === "CRITICAL"
                              ? "bg-red-500/20 text-red-300 border-red-500/40"
                              : point.risk_level === "HIGH"
                              ? "bg-orange-500/20 text-orange-300 border-orange-500/40"
                              : "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                          }`}
                        >
                          {point.risk_level} RISK
                        </span>
                        <span className="text-[10px] font-mono text-slate-400">
                          SII: <strong className="text-cyan-400">{point.sii_score}</strong>
                        </span>
                      </div>

                      <div>
                        <h4 className="text-sm font-bold text-white leading-tight">
                          {point.site_name}
                        </h4>
                        <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                          {point.region} • {point.operation_type}
                        </p>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-xs font-mono bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase">Current SIF</div>
                          <div className="text-sm font-bold text-amber-400 mt-0.5">
                            {Math.round(point.current_density * 100)}%
                          </div>
                        </div>
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase">30-Day Forecast</div>
                          <div className="text-sm font-bold text-red-400 mt-0.5">
                            {Math.round(point.forecast_density * 100)}%
                          </div>
                        </div>
                      </div>

                      <div className="text-[11px] text-slate-300">
                        <span className="text-slate-500 font-mono block text-[10px] uppercase">
                          Primary Vulnerability:
                        </span>
                        <span className="font-semibold text-amber-300">{point.top_risk_factor}</span>
                      </div>

                      <div className="pt-2 border-t border-slate-800 flex justify-between items-center text-xs font-mono">
                        <Link
                          to={`/sites`}
                          className="text-cyan-400 hover:text-cyan-300 flex items-center space-x-1"
                        >
                          <span>Inspect in SII Table</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </div>
                  </Popup>
                </Marker>
              </React.Fragment>
            );
          })}
        </MapContainer>

        {/* ================= MAP OVERLAY FLOATING CONTROLS ================= */}
        {/* Top-Right: Map Legend Overlay */}
        <div className="absolute top-4 right-4 z-[400] p-3.5 rounded-xl bg-[#0c1322]/95 border border-slate-800/90 shadow-2xl backdrop-blur-md space-y-2.5 text-xs font-mono text-slate-300 max-w-xs pointer-events-auto">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="font-bold text-white uppercase text-[11px] flex items-center space-x-1.5">
              <Layers className="w-3.5 h-3.5 text-amber-400" />
              <span>Risk Thresholds</span>
            </span>
            <span className="text-[10px] text-slate-500">
              {viewMode === "forecast" ? "30d Forecast" : "Current"}
            </span>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
                <span>Critical (≥ 35%)</span>
              </div>
              <span className="text-red-400 font-bold">Immediate Action</span>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="w-3 h-3 rounded-full bg-orange-400" />
                <span>High (22% – 35%)</span>
              </div>
              <span className="text-orange-300 font-bold">Heightened</span>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="w-3 h-3 rounded-full bg-amber-400" />
                <span>Moderate (12% – 22%)</span>
              </div>
              <span className="text-amber-300 font-bold">Standard Alert</span>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="w-3 h-3 rounded-full bg-emerald-400" />
                <span>Routine (&lt; 12%)</span>
              </div>
              <span className="text-emerald-300 font-bold">Normal Ops</span>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
            <span className="text-[11px] text-slate-400">Hazard Radius Rings:</span>
            <button
              onClick={() => setShowRadiusRings(!showRadiusRings)}
              className={`px-2 py-0.5 rounded text-[10px] font-bold border transition ${
                showRadiusRings
                  ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40"
                  : "bg-slate-900 text-slate-500 border-slate-800"
              }`}
            >
              {showRadiusRings ? "ENABLED" : "HIDDEN"}
            </button>
          </div>
        </div>

        {/* Bottom-Left: Selected Asset Inspection Card */}
        {selectedPoint && (
          <div className="absolute bottom-4 left-4 z-[400] p-4 rounded-xl bg-[#090e18]/95 border border-slate-800 shadow-2xl backdrop-blur-md max-w-sm w-full space-y-3 pointer-events-auto animate-in slide-in-from-bottom-2 duration-300">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <MapPin className="w-4 h-4 text-amber-400" />
                <h3 className="text-xs font-bold text-white font-mono truncate max-w-[200px]">
                  {selectedPoint.site_name}
                </h3>
              </div>
              <span
                className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border ${
                  selectedPoint.risk_level === "CRITICAL"
                    ? "bg-red-500/20 text-red-300 border-red-500/40"
                    : "bg-amber-500/20 text-amber-300 border-amber-500/40"
                }`}
              >
                {selectedPoint.risk_level}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="p-2 rounded bg-slate-950 border border-slate-800">
                <div className="text-[9px] text-slate-500 uppercase">Current Density</div>
                <div className="text-sm font-bold text-amber-400 mt-0.5">
                  {Math.round(selectedPoint.current_density * 100)}%
                </div>
              </div>

              <div className="p-2 rounded bg-slate-950 border border-slate-800">
                <div className="text-[9px] text-slate-500 uppercase">30-Day Forecast</div>
                <div className="text-sm font-bold text-red-400 mt-0.5 flex items-center space-x-1">
                  <span>{Math.round(selectedPoint.forecast_density * 100)}%</span>
                  {selectedPoint.forecast_trend === "rising" ? (
                    <TrendingUp className="w-3.5 h-3.5 text-red-400" />
                  ) : selectedPoint.forecast_trend === "falling" ? (
                    <TrendingDown className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Minus className="w-3.5 h-3.5 text-slate-400" />
                  )}
                </div>
              </div>
            </div>

            <div className="text-[11px] font-mono text-slate-300 flex items-center justify-between">
              <span className="text-slate-500">Predicted 30d Breaches:</span>
              <span className="font-bold text-white">~{selectedPoint.predicted_breaches_next_30d} events</span>
            </div>

            <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">Hazard Zone: {selectedPoint.risk_radius_meters}m</span>
              <Link
                to={`/sites`}
                className="text-amber-400 hover:text-amber-300 font-bold flex items-center space-x-1"
              >
                <span>What-If Sim</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
