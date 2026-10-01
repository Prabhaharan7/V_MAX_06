from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class AlertItem(BaseModel):
    id: int
    report_id: Optional[int] = None
    severity: str = Field(..., description="'CRITICAL', 'HIGH', 'MEDIUM', or 'LOW'")
    title: str = Field(..., description="Alert headline summary")
    site_name: str = Field(..., description="Affected asset, rig, or station")
    region: str = Field(default="Assam", description="Operational sector")
    operation_type: str = Field(default="Drilling", description="Operation type")
    timestamp: datetime = Field(..., description="Timestamp of alert generation")
    time_ago: Optional[str] = None
    description: str = Field(..., description="Detailed operational hazard description")
    lsr_category: str = Field(..., description="Primary Life-Saving Rule breach category")
    compromised_barrier: Optional[str] = Field(default=None, description="Compromised safety barrier")
    alert_type: str = Field(default="In-App Push", description="SMS, Email, or In-App Push")
    sent_to: str = Field(default="HSE Officer & Rig Superintendent", description="Target recipient roles")
    acknowledged: bool = Field(default=False, description="Whether alert has been acknowledged by safety officer")
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


class AlertAcknowledgeResponse(BaseModel):
    success: bool = True
    alert_id: int
    acknowledged: bool = True
    acknowledged_at: datetime
    message: str


class AlertStatsResponse(BaseModel):
    total_active_alerts: int
    unacknowledged_count: int
    critical_count: int
    high_count: int
    last_triggered_at: Optional[datetime] = None
