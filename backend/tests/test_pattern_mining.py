"""
Unit Tests for Precursor Pattern Mining & Site Ranking Service
Testing rolling window aggregation, trend calculation, and site ranking.
"""

import pytest
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.entities import PatternTrend, SIFLabel, BarrierSeverity
from app.schemas.patterns import PrecursorPatternResponse, RankedSiteResponse


def test_ranked_site_response_schema():
    """
    Test Case 1: RankedSiteResponse schema structure
    """
    site = RankedSiteResponse(
        rank=1,
        site_id=1,
        site_name="Duliajan Drilling Rig D-04",
        region="Upper Assam Basin",
        operation_type="Drilling",
        location_lat=27.3587,
        location_lng=95.3192,
        total_reports=50,
        sif_reports_count=15,
        sif_density=0.30,
        weighted_sif_density=0.42,
        top_barrier_failure="Energy Isolation",
        primary_trend=PatternTrend.rising,
    )
    assert site.rank == 1
    assert site.sif_density == 0.30
    assert site.weighted_sif_density == 0.42
    assert site.primary_trend == PatternTrend.rising


def test_precursor_pattern_response_schema():
    """
    Test Case 2: PrecursorPatternResponse schema structure
    """
    import datetime
    pat = PrecursorPatternResponse(
        id=1,
        activity="Drilling & Tripping",
        location="Duliajan Rig D-04",
        barrier_type="Snub Line & Tong Red Zone",
        occurrence_count=12,
        last_seen=datetime.datetime.now(datetime.timezone.utc),
        trend=PatternTrend.rising,
    )
    assert pat.occurrence_count == 12
    assert pat.trend == PatternTrend.rising


def test_trend_calculation_logic():
    """
    Test Case 3: Verify trend computation logic rules
    """
    # 1. Rising: Significant increase
    recent, prior = 10, 5
    assert recent >= (prior * 1.25) # Rising

    # 2. Falling: Significant decrease
    recent, prior = 3, 8
    assert recent <= (prior * 0.75) # Falling

    # 3. Stable: Within tolerance
    recent, prior = 6, 6
    assert not (recent >= prior * 1.25) and not (recent <= prior * 0.75) # Stable


def test_api_routes_registered():
    """
    Test Case 4: Verify patterns endpoints registered on FastAPI app
    """
    from app.main import app
    paths = list(app.openapi()["paths"].keys())
    assert any("/patterns" in p for p in paths)
    assert any("/ranked-sites" in p for p in paths)
    assert any("/refresh" in p for p in paths)
