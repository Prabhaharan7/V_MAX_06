import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import (
    BarrierFailure,
    BarrierSeverity,
    PatternTrend,
    PrecursorPattern,
    Report,
    ReportStatus,
    SIFLabel,
    Site,
)
from app.schemas.patterns import RankedSiteResponse

logger = logging.getLogger("sif_sentinel.pattern_mining")


# ==============================================================================
# 1. Scheduled / On-Demand Pattern Mining Aggregation
# ==============================================================================

async def run_pattern_mining(db: AsyncSession) -> List[PrecursorPattern]:
    """
    Groups reports by (activity, site location, barrier_type) combinations,
    counts occurrences over a rolling 90-day window, computes trends
    (rising, stable, falling by comparing against the prior 90-day window),
    and upserts the results into the precursor_patterns table.
    """
    now = datetime.now(timezone.utc)
    recent_90d_start = now - timedelta(days=90)
    prior_90d_start = now - timedelta(days=180)

    # 1. Fetch all reports from the last 180 days with site and barrier failure relations
    stmt = (
        select(Report)
        .options(
            selectinload(Report.site),
            selectinload(Report.barrier_failures),
        )
        .where(Report.submitted_at >= prior_90d_start)
    )
    result = await db.execute(stmt)
    reports = result.scalars().all()

    # Track metrics per (activity, location, barrier_type)
    # Key: (activity, location, barrier_type) -> {"recent_count": int, "prior_count": int, "last_seen": datetime}
    pattern_buckets: Dict[Tuple[str, str, str], Dict[str, Any]] = defaultdict(
        lambda: {"recent_count": 0, "prior_count": 0, "last_seen": datetime.min.replace(tzinfo=timezone.utc)}
    )

    for rep in reports:
        activity = rep.activity or "General Operations"
        location = rep.site.name if rep.site else "Oilfield Site"
        submitted_at = rep.submitted_at
        if submitted_at.tzinfo is None:
            submitted_at = submitted_at.replace(tzinfo=timezone.utc)

        # Extract barrier types associated with report
        barrier_types = []
        if rep.barrier_failures:
            barrier_types = [bf.barrier_type for bf in rep.barrier_failures if bf.barrier_type]
        if not barrier_types:
            if rep.primary_lsr:
                barrier_types = [rep.primary_lsr]
            else:
                barrier_types = ["General Safety Control"]

        for b_type in set(barrier_types):
            key = (activity, location, b_type)
            bucket = pattern_buckets[key]

            # Track latest occurrence timestamp
            if submitted_at > bucket["last_seen"]:
                bucket["last_seen"] = submitted_at

            # Tally counts across rolling windows
            if submitted_at >= recent_90d_start:
                bucket["recent_count"] += 1
            else:
                bucket["prior_count"] += 1

    # 2. Compute trends and upsert into precursor_patterns table
    upserted_patterns: List[PrecursorPattern] = []

    for (activity, location, b_type), data in pattern_buckets.items():
        recent_count = data["recent_count"]
        prior_count = data["prior_count"]
        last_seen = data["last_seen"]

        # Only register patterns with activity in the last 180 days
        total_occurrences = recent_count + prior_count
        if total_occurrences == 0:
            continue

        # Effective count is recent 90-day count, or total if recent is 0
        effective_count = recent_count if recent_count > 0 else prior_count

        # Trend calculation logic
        if recent_count > prior_count:
            if prior_count == 0 and recent_count >= 2:
                trend = PatternTrend.rising
            elif prior_count > 0 and recent_count >= (prior_count * 1.25):
                trend = PatternTrend.rising
            else:
                trend = PatternTrend.stable
        elif recent_count < prior_count:
            if recent_count <= (prior_count * 0.75):
                trend = PatternTrend.falling
            else:
                trend = PatternTrend.stable
        else:
            trend = PatternTrend.stable

        # Check existing record in DB
        pattern_stmt = select(PrecursorPattern).where(
            PrecursorPattern.activity == activity,
            PrecursorPattern.location == location,
            PrecursorPattern.barrier_type == b_type,
        )
        existing_pattern = (await db.execute(pattern_stmt)).scalar_one_or_none()

        if existing_pattern:
            existing_pattern.occurrence_count = effective_count
            existing_pattern.last_seen = last_seen
            existing_pattern.trend = trend
            upserted_patterns.append(existing_pattern)
        else:
            new_pattern = PrecursorPattern(
                activity=activity,
                location=location,
                barrier_type=b_type,
                occurrence_count=effective_count,
                last_seen=last_seen,
                trend=trend,
            )
            db.add(new_pattern)
            upserted_patterns.append(new_pattern)

    await db.commit()
    logger.info(f"Pattern mining complete: {len(upserted_patterns)} patterns aggregated and upserted.")
    return upserted_patterns


# ==============================================================================
# 2. Query Precursor Patterns with Filters
# ==============================================================================

async def get_patterns(
    db: AsyncSession,
    site_id: Optional[int] = None,
    min_count: int = 1,
    trend: Optional[PatternTrend] = None,
    limit: int = 50,
) -> List[PrecursorPattern]:
    """
    Retrieves ranked precursor patterns ordered by occurrence count and recency.
    Optionally filtered by site ID, minimum count, and trend.
    """
    query = select(PrecursorPattern).where(PrecursorPattern.occurrence_count >= min_count)

    if site_id is not None:
        site_stmt = select(Site.name).where(Site.id == site_id)
        site_name = (await db.execute(site_stmt)).scalar_one_or_none()
        if site_name:
            # Match location prefix or name substring
            query = query.where(PrecursorPattern.location.ilike(f"%{site_name[:15]}%"))

    if trend is not None:
        query = query.where(PrecursorPattern.trend == trend)

    query = query.order_by(
        desc(PrecursorPattern.occurrence_count),
        desc(PrecursorPattern.last_seen),
    ).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


# ==============================================================================
# 3. Main Dashboard: Site Ranking by SIF-Precursor Density & Barrier Severity
# ==============================================================================

async def get_ranked_sites(db: AsyncSession) -> List[RankedSiteResponse]:
    """
    Calculates SIF-precursor density for each site:
    (sum of SIF-potential reports / total reports at that site, weighted by barrier failure severity)
    and returns a ranked list of sites for the main executive safety dashboard.
    """
    # 1. Fetch all sites
    sites_stmt = select(Site).order_by(Site.id)
    sites = (await db.execute(sites_stmt)).scalars().all()

    if not sites:
        return []

    # 2. Fetch all precursor patterns to infer site-level trends
    patterns_stmt = select(PrecursorPattern)
    patterns = (await db.execute(patterns_stmt)).scalars().all()
    site_trends: Dict[str, List[PatternTrend]] = defaultdict(list)
    for p in patterns:
        site_trends[p.location].append(p.trend)

    ranked_list: List[RankedSiteResponse] = []

    for site in sites:
        # Tally total reports at this site
        total_stmt = select(func.count(Report.id)).where(Report.site_id == site.id)
        total_reports = (await db.execute(total_stmt)).scalar() or 0

        # Tally SIF-potential reports at this site
        sif_stmt = select(func.count(Report.id)).where(
            Report.site_id == site.id,
            Report.sif_label == SIFLabel.sif_potential,
        )
        sif_reports_count = (await db.execute(sif_stmt)).scalar() or 0

        # Fetch barrier failures at this site with severity weights
        bf_stmt = (
            select(BarrierFailure.barrier_type, BarrierFailure.severity, func.count(BarrierFailure.id))
            .join(Report, BarrierFailure.report_id == Report.id)
            .where(Report.site_id == site.id)
            .group_by(BarrierFailure.barrier_type, BarrierFailure.severity)
        )
        bf_results = (await db.execute(bf_stmt)).all()

        weighted_severity_score = 0.0
        barrier_counts: Dict[str, int] = defaultdict(int)

        # Severity weights: High = 2.0x, Medium = 1.2x, Low = 0.6x
        severity_weight_map = {
            BarrierSeverity.high: 2.0,
            BarrierSeverity.medium: 1.2,
            BarrierSeverity.low: 0.6,
        }

        for b_type, severity, count in bf_results:
            w = severity_weight_map.get(severity, 1.0)
            weighted_severity_score += (count * w)
            barrier_counts[b_type] += count

        # Top recurring barrier failure
        top_barrier = max(barrier_counts, key=barrier_counts.get) if barrier_counts else None

        # Calculate Densities
        sif_density = round(sif_reports_count / total_reports, 3) if total_reports > 0 else 0.0
        # Weighted SIF density combines base SIF ratio with severity weight amplification
        if total_reports > 0:
            weighted_sif_density = round(
                (sif_reports_count * 1.0 + (weighted_severity_score * 0.4)) / total_reports, 3
            )
        else:
            weighted_sif_density = 0.0

        # Infer Primary Trend for the site
        matched_trends = []
        for loc_key, t_list in site_trends.items():
            if site.name[:12].lower() in loc_key.lower():
                matched_trends.extend(t_list)

        if PatternTrend.rising in matched_trends:
            primary_trend = PatternTrend.rising
        elif PatternTrend.falling in matched_trends and PatternTrend.rising not in matched_trends:
            primary_trend = PatternTrend.falling
        else:
            primary_trend = PatternTrend.stable

        ranked_list.append(
            RankedSiteResponse(
                rank=0, # Populated after sorting
                site_id=site.id,
                site_name=site.name,
                region=site.region,
                operation_type=site.operation_type,
                location_lat=site.location_lat,
                location_lng=site.location_lng,
                total_reports=total_reports,
                sif_reports_count=sif_reports_count,
                sif_density=sif_density,
                weighted_sif_density=weighted_sif_density,
                top_barrier_failure=top_barrier,
                primary_trend=primary_trend,
            )
        )

    # 3. Sort sites descending by weighted_sif_density, sif_density, and sif_reports_count
    ranked_list.sort(
        key=lambda s: (s.weighted_sif_density, s.sif_density, s.sif_reports_count),
        reverse=True,
    )

    # 4. Assign 1-indexed ranks
    for index, site_item in enumerate(ranked_list, start=1):
        site_item.rank = index

    return ranked_list
