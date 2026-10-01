from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class HeatmapForecastPoint(BaseModel):
    site_id: int
    site_name: str
    region: str
    operation_type: str
    location_lat: float
    location_lng: float
    current_density: float = Field(..., description="Current SIF precursor density (0.0 to 1.0)")
    forecast_density: float = Field(..., description="Projected 30-day SIF precursor density (0.0 to 1.0)")
    forecast_trend: str = Field(default="rising", description="'rising', 'stable', or 'falling'")
    risk_level: str = Field(..., description="'CRITICAL', 'HIGH', 'MODERATE', or 'LOW'")
    sii_score: float = Field(default=75.0, description="Safety Improvement Index score")
    top_risk_factor: str = Field(..., description="Primary identified risk factor or barrier vulnerability")
    active_precursors_30d: int = Field(default=0, description="Precursors in the last 30 days")
    predicted_breaches_next_30d: int = Field(default=0, description="Forecasted precursor events over next 30 days")
    risk_radius_meters: int = Field(default=1500, description="Hazard impact zone radius in meters")


class ForecastHeatmapResponse(BaseModel):
    timestamp: datetime
    forecast_horizon_days: int = 30
    total_sites_monitored: int
    critical_hotspots_count: int
    sites: List[HeatmapForecastPoint]
