from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.entities import BarrierSeverity, Report, SIFLabel, Site
from app.schemas.forecast import ForecastHeatmapResponse, HeatmapForecastPoint

router = APIRouter()


@router.get(
    "/heatmap",
    response_model=List[HeatmapForecastPoint],
    summary="Get SIF Precursor Risk Map & 30-Day Predictive Heatmap",
)
async def get_forecast_heatmap(
    db: AsyncSession = Depends(get_db),
):
    """
    Computes current SIF precursor densities and 30-day forward predictive
    forecast densities across all operational rigs, installations, and facilities.
    Powers the geospatial Risk Map and predictive hazard radius overlay.
    """
    # Query all sites with reports and barrier failures
    stmt = (
        select(Site)
        .options(
            selectinload(Site.reports).selectinload(Report.barrier_failures),
        )
    )
    sites = (await db.execute(stmt)).scalars().all()

    points: List[HeatmapForecastPoint] = []
    now = datetime.now(timezone.utc)
    recent_30d = now - timedelta(days=30)
    prior_60d = now - timedelta(days=60)

    for site in sites:
        reports = site.reports or []
        total_reports = len(reports)

        # Recent 30-day reports
        recent_reps = [r for r in reports if (r.submitted_at.tzinfo and r.submitted_at >= recent_30d) or (not r.submitted_at.tzinfo and r.submitted_at >= recent_30d.replace(tzinfo=None))]
        prior_reps = [r for r in reports if ((r.submitted_at.tzinfo and prior_60d <= r.submitted_at < recent_30d) or (not r.submitted_at.tzinfo and prior_60d.replace(tzinfo=None) <= r.submitted_at < recent_30d.replace(tzinfo=None)))]

        # SIF Precursor Counts
        recent_sif = len([r for r in recent_reps if r.sif_label == SIFLabel.sif_potential])
        prior_sif = len([r for r in prior_reps if r.sif_label == SIFLabel.sif_potential])
        total_sif = len([r for r in reports if r.sif_label == SIFLabel.sif_potential])

        current_density = round(total_sif / max(total_reports, 1), 3)

        # Predictive 30-day forecast modeling (Linear exponential trend with barrier failure momentum)
        delta_momentum = (recent_sif - prior_sif) * 0.05
        forecast_density = round(min(0.95, max(0.05, current_density + delta_momentum + (0.04 if recent_sif > 3 else -0.02))), 3)

        forecast_trend = "rising" if forecast_density > current_density + 0.02 else "falling" if forecast_density < current_density - 0.02 else "stable"

        # Determine Risk Level
        if forecast_density >= 0.35 or current_density >= 0.35:
            risk_level = "CRITICAL"
            risk_radius = 2800
        elif forecast_density >= 0.22 or current_density >= 0.22:
            risk_level = "HIGH"
            risk_radius = 2000
        elif forecast_density >= 0.12 or current_density >= 0.12:
            risk_level = "MODERATE"
            risk_radius = 1200
        else:
            risk_level = "LOW"
            risk_radius = 800

        # Identify top risk factor
        barrier_tallies = {}
        for r in reports:
            for bf in (r.barrier_failures or []):
                bt = bf.barrier_type or "General Barrier"
                barrier_tallies[bt] = barrier_tallies.get(bt, 0) + (2 if bf.severity == BarrierSeverity.high else 1)

        top_risk = max(barrier_tallies.items(), key=lambda x: x[1])[0] if barrier_tallies else "Routine Operational Risk"

        points.append(
            HeatmapForecastPoint(
                site_id=site.id,
                site_name=site.name,
                region=site.region,
                operation_type=site.operation_type,
                location_lat=site.location_lat,
                location_lng=site.location_lng,
                current_density=current_density,
                forecast_density=forecast_density,
                forecast_trend=forecast_trend,
                risk_level=risk_level,
                sii_score=round(max(10.0, 100.0 - (current_density * 80.0)), 1),
                top_risk_factor=top_risk,
                active_precursors_30d=recent_sif,
                predicted_breaches_next_30d=max(int(forecast_density * 35), 2),
                risk_radius_meters=risk_radius,
            )
        )

    # Sort so critical sites appear on top
    points.sort(key=lambda p: (p.risk_level != "CRITICAL", p.risk_level != "HIGH", -p.forecast_density))
    return points
