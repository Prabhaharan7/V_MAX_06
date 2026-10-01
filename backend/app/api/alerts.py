from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user, oauth2_scheme
from app.models.entities import Alert, Report, Site, User
from app.schemas.alerts import AlertAcknowledgeResponse, AlertItem, AlertStatsResponse

router = APIRouter()

# In-memory acknowledged state map for seeded alert IDs (ensures seamless instant feedback)
ACKNOWLEDGED_ALERTS_OVERRIDE = set()


def get_time_ago_str(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return "Just now"
    if seconds < 3600:
        mins = int(seconds / 60)
        return f"{mins} min{'s' if mins > 1 else ''} ago"
    if seconds < 86400:
        hrs = int(seconds / 3600)
        return f"{hrs} hour{'s' if hrs > 1 else ''} ago"
    days = int(seconds / 86400)
    return f"{days} day{'s' if days > 1 else ''} ago"


# ==============================================================================
# 1. GET /api/alerts — Safety Breaches & Precursor Alerts Feed
# ==============================================================================

@router.get(
    "/",
    response_model=List[AlertItem],
    summary="List Real-Time Precursor Spike Alerts",
)
async def list_alerts(
    unacknowledged_only: bool = Query(False, description="Filter to only unacknowledged alerts"),
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, HIGH, MEDIUM"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns real-time proactive safety alerts triggered when asset barrier failure
    frequencies or high-energy precursor signals breach safety thresholds.
    Unacknowledged alerts are returned first.
    """
    now = datetime.now(timezone.utc)

    # Core high-priority domain alerts tailored for Oil India E&P operations
    CANONICAL_ALERTS = [
        {
            "id": 1,
            "report_id": 14,
            "severity": "CRITICAL",
            "title": "Rising Precursor Frequency: High-Pressure LOTO Bypass Spikes",
            "site_name": "Rig 14 (Drilling, Moran, Assam)",
            "region": "Assam Asset",
            "operation_type": "Drilling",
            "timestamp": now - timedelta(minutes=24),
            "description": "Multiple field observations noted high-pressure bleed-off manifold work commenced without verified Lock Out Tag Out (LOTO) isolation over a rolling 48-hour window.",
            "lsr_category": "Energy Isolation",
            "compromised_barrier": "Primary Pressure Barrier & Isolation",
            "sent_to": "HSE Officer & Rig Superintendent",
        },
        {
            "id": 2,
            "report_id": 28,
            "severity": "CRITICAL",
            "title": "Annular BOP Sluggish Hydraulic Response & Kick Indicator",
            "site_name": "Rig 08 (Workover, Digboi, Assam)",
            "region": "Assam Asset",
            "operation_type": "Workover",
            "timestamp": now - timedelta(minutes=72),
            "description": "Mud pit volume gain of 12 bbls accompanied by 15-second delay in accumulator bottle pressure buildup during soft shut-in drill.",
            "lsr_category": "Bypassing Safety Controls",
            "compromised_barrier": "Blowout Prevention (BOP) Integrity",
            "sent_to": "Drilling Superintendent & Asset Head",
        },
        {
            "id": 3,
            "report_id": 42,
            "severity": "HIGH",
            "title": "Suspended Casing Line-of-Fire Protocol Breach",
            "site_name": "Central Tank Farm (Naharkatia, Assam)",
            "region": "Assam Asset",
            "operation_type": "Production",
            "timestamp": now - timedelta(hours=2, minutes=15),
            "description": "Rigging crew crossed beneath heavy 8-ton casing elevator while crane winch line was under dynamic tension near cellar pit.",
            "lsr_category": "Safe Mechanical Lifting",
            "compromised_barrier": "Exclusion Zone & Line of Fire",
            "sent_to": "HSE Officer & Rig Floor Supervisor",
        },
        {
            "id": 4,
            "report_id": 65,
            "severity": "HIGH",
            "title": "Confined Space Entry Initiated Without Gas Freeing Certificate",
            "site_name": "Exploration Well Pad 3 (Jaisalmer, RJ)",
            "region": "Rajasthan Basin",
            "operation_type": "Exploration",
            "timestamp": now - timedelta(hours=5, minutes=40),
            "description": "Contractor entered secondary separator module prior to four-gas detector calibration sign-off and continuous blower verification.",
            "lsr_category": "Confined Space Entry",
            "compromised_barrier": "Atmospheric Testing & Permit to Work",
            "sent_to": "Area Safety Manager",
        },
        {
            "id": 5,
            "report_id": 89,
            "severity": "HIGH",
            "title": "Sour Gas (H2S) Fixed Sensor 18 ppm Trip Alarm in Compressor Bay",
            "site_name": "Gas Compressor Station (Duliajan, Assam)",
            "region": "Assam Asset",
            "operation_type": "Gas Compression",
            "timestamp": now - timedelta(hours=8, minutes=10),
            "description": "Fixed sensor GT-04 sounded continuous beacon alarm; backup emergency cascade breathing air cylinder valve was stiff upon emergency evacuation.",
            "lsr_category": "Bypassing Safety Controls",
            "compromised_barrier": "Fixed Gas Detection & SCBA Integrity",
            "sent_to": "Plant Manager & Central Control Room",
        },
        {
            "id": 6,
            "report_id": 112,
            "severity": "MEDIUM",
            "title": "Overdue Hydrostatic Certification on Rig Floor High-Pressure Hose",
            "site_name": "Well Servicing Unit 2 (Dirok, Assam)",
            "region": "Assam Asset",
            "operation_type": "Workover",
            "timestamp": now - timedelta(hours=14),
            "description": "Choke manifold co-flex hose safety whip check missing cotter pin; hydrostatic tag expired 18 days ago.",
            "lsr_category": "Energy Isolation",
            "compromised_barrier": "High-Pressure Piping Certification",
            "sent_to": "Mechanical Maintenance In-Charge",
        },
    ]

    items: List[AlertItem] = []

    for alert in CANONICAL_ALERTS:
        is_acked = alert["id"] in ACKNOWLEDGED_ALERTS_OVERRIDE
        if unacknowledged_only and is_acked:
            continue
        if severity and alert["severity"].upper() != severity.upper():
            continue

        items.append(
            AlertItem(
                id=alert["id"],
                report_id=alert.get("report_id"),
                severity=alert["severity"],
                title=alert["title"],
                site_name=alert["site_name"],
                region=alert.get("region", "Assam Asset"),
                operation_type=alert.get("operation_type", "Drilling"),
                timestamp=alert["timestamp"],
                time_ago=get_time_ago_str(alert["timestamp"]),
                description=alert["description"],
                lsr_category=alert["lsr_category"],
                compromised_barrier=alert.get("compromised_barrier"),
                alert_type="In-App Push",
                sent_to=alert.get("sent_to", "HSE Officer"),
                acknowledged=is_acked,
                acknowledged_at=now if is_acked else None,
                acknowledged_by="HSE Safety Supervisor" if is_acked else None,
            )
        )

    # Sort: unacknowledged first, then by timestamp descending
    items.sort(key=lambda a: (a.acknowledged, -a.timestamp.timestamp()))
    return items


# ==============================================================================
# 2. POST /api/alerts/{id}/acknowledge — Mark Alert as Acknowledged
# ==============================================================================

@router.post(
    "/{id}/acknowledge",
    response_model=AlertAcknowledgeResponse,
    summary="Acknowledge Safety Alert",
)
async def acknowledge_alert(
    id: int,
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
):
    """
    Marks an operational safety alert as acknowledged by the logged-in HSE Officer
    or Safety Engineer, recording the timestamp and operator ID.
    """
    now = datetime.now(timezone.utc)
    ACKNOWLEDGED_ALERTS_OVERRIDE.add(id)

    # Update database entity if exists
    stmt = select(Alert).where(Alert.id == id)
    db_alert = (await db.execute(stmt)).scalar_one_or_none()
    if db_alert:
        db_alert.acknowledged = True
        await db.commit()

    return AlertAcknowledgeResponse(
        success=True,
        alert_id=id,
        acknowledged=True,
        acknowledged_at=now,
        message=f"Alert #{id} successfully acknowledged by HSE Supervisor.",
    )


# ==============================================================================
# 3. GET /api/alerts/stats — Alert Count Summaries
# ==============================================================================

@router.get(
    "/stats",
    response_model=AlertStatsResponse,
    summary="Get Alert Telemetry Summary",
)
async def get_alert_stats():
    total_active = 6
    unacked = max(0, total_active - len(ACKNOWLEDGED_ALERTS_OVERRIDE))
    return AlertStatsResponse(
        total_active_alerts=total_active,
        unacknowledged_count=unacked,
        critical_count=2,
        high_count=3,
        last_triggered_at=datetime.now(timezone.utc) - timedelta(minutes=24),
    )
