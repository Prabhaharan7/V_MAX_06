"""
================================================================================
SIF Sentinel AI - Database Models & Foreign Key Relationship Diagram
SIH 2026 Problem Statement PS 26165 (Oil India Limited)
================================================================================

                               +--------------------+
                               |       sites        |
                               +--------------------+
                                 | 1            | 1
                                 |              |
                                 | *            | *
                               +-------+      +---------------+
                               | users |      | safety_index  |
                               +-------+      +---------------+
                                 | 1    | 1            |
                                 |      +--------------+-----+
                                 |                           |
                                 | * (submitted_by)          | * (assigned_to / corrected_by / actor)
                               +---------+                   |
                               | reports |<------------------+
                               +---------+                   |
                                 | 1                         |
                  +--------------+---------------+-----------+----------+
                  | *            | *             | *                    | *
         +-----------------+ +------------------+ +--------------+ +--------------------+
         | report_lsr_tags | | barrier_failures | | review_queue | | model_feedback_log |
         +-----------------+ +------------------+ +--------------+ +--------------------+
                                                 |                      |
                                                 | *                    |
                                            +---------+                 |
                                            | alerts  |                 |
                                            +---------+                 |
                                                                        |
                                            +------------------+        |
                                            | precursor_pattern|        |
                                            | (Aggregated)     |        |
                                            +------------------+        |
                                                                        |
                                            +-----------+               |
                                            | audit_log |<--------------+
                                            +-----------+

================================================================================
"""

import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Enum as SQLEnum,
    Index,
    func,
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, JSON
from app.core.database import Base


class SafeVector(TypeDecorator):
    """
    PostgreSQL pgvector Vector(384) with seamless JSON/SQLite compatibility for local testing.
    """
    impl = JSON
    cache_ok = True

    def __init__(self, dim: int = 384, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            try:
                from pgvector.sqlalchemy import Vector
                return dialect.type_descriptor(Vector(self.dim))
            except Exception:
                return dialect.type_descriptor(JSON())
        return dialect.type_descriptor(JSON())


# ==========================================
# Enumerations
# ==========================================

class UserRole(str, enum.Enum):
    hse_officer = "hse_officer"
    site_manager = "site_manager"
    admin = "admin"


class ReportType(str, enum.Enum):
    UA = "UA"                    # Unsafe Act
    UC = "UC"                    # Unsafe Condition
    near_miss = "near_miss"      # Near Miss
    incident = "incident"        # Incident / Recordable


class SIFLabel(str, enum.Enum):
    sif_potential = "sif_potential"
    non_sif = "non_sif"


class ReportStatus(str, enum.Enum):
    pending_review = "pending_review"
    reviewed = "reviewed"
    auto_confirmed = "auto_confirmed"


class BarrierSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class PatternTrend(str, enum.Enum):
    rising = "rising"
    stable = "stable"
    falling = "falling"


# ==========================================
# Database Table Entities
# ==========================================

class Site(Base):
    """
    Oil India operational installation, drilling rig, production station or refinery hub.
    """
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    location_lat = Column(Float, nullable=False)
    location_lng = Column(Float, nullable=False)
    region = Column(String(100), nullable=False)
    operation_type = Column(String(100), nullable=False) # Drilling, Production, Pipeline, Exploration, Refining

    # Relationships
    users = relationship("User", back_populates="site")
    reports = relationship("Report", back_populates="site", cascade="all, delete-orphan")
    safety_indices = relationship("SafetyIndex", back_populates="site", cascade="all, delete-orphan")


class User(Base):
    """
    HSE officers, site managers, safety supervisors, and admins.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole, name="user_role_enum"), nullable=False, default=UserRole.hse_officer)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    site = relationship("Site", back_populates="users")
    submitted_reports = relationship("Report", back_populates="submitter", foreign_keys="Report.submitted_by")
    assigned_reviews = relationship("ReviewQueue", back_populates="assignee", foreign_keys="ReviewQueue.assigned_to")
    feedback_logs = relationship("ModelFeedbackLog", back_populates="feedback_user", foreign_keys="ModelFeedbackLog.corrected_by")
    audit_logs = relationship("AuditLog", back_populates="actor_user", foreign_keys="AuditLog.actor")


class Report(Base):
    """
    Core safety report entity storing observations, translated text,
    AI SIF precursor classification, and pgvector embeddings.
    """
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(SQLEnum(ReportType, name="report_type_enum"), nullable=False, default=ReportType.near_miss)
    raw_text = Column(Text, nullable=False)
    submitted_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    activity = Column(String(255), nullable=False)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    language = Column(String(10), nullable=False, default="en")
    translated_text = Column(Text, nullable=True)
    sif_label = Column(SQLEnum(SIFLabel, name="sif_label_enum"), nullable=True, index=True)
    sif_confidence = Column(Float, nullable=True)
    primary_lsr = Column(String(255), nullable=True, index=True)
    status = Column(SQLEnum(ReportStatus, name="report_status_enum"), nullable=False, default=ReportStatus.pending_review)
    embedding = Column(SafeVector(384), nullable=True)
    raw_metadata = Column(JSON, nullable=True)

    # Bulk Upload Batch & Ground-Truth Benchmarking Fields
    upload_batch_id = Column(String(100), nullable=True, index=True)
    upload_batch_label = Column(String(255), nullable=True)
    ground_truth_sif_label = Column(String(50), nullable=True, index=True)
    ground_truth_lsr = Column(String(255), nullable=True, index=True)
    ground_truth_barrier_status = Column(String(255), nullable=True)
    ground_truth_split = Column(String(50), nullable=True, index=True)

    # Relationships
    submitter = relationship("User", back_populates="submitted_reports", foreign_keys=[submitted_by])
    site = relationship("Site", back_populates="reports", foreign_keys=[site_id])
    lsr_tags = relationship("ReportLSRTag", back_populates="report", cascade="all, delete-orphan")
    barrier_failures = relationship("BarrierFailure", back_populates="report", cascade="all, delete-orphan")
    review_queue_entries = relationship("ReviewQueue", back_populates="report", cascade="all, delete-orphan")
    feedback_logs = relationship("ModelFeedbackLog", back_populates="report", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="report", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_reports_site_submitted", "site_id", "submitted_at"),
        Index("ix_reports_sif_status", "sif_label", "status"),
    )


class ReportLSRTag(Base):
    """
    Life-Saving Rules (LSR) tags mapped to the report with model confidence.
    """
    __tablename__ = "report_lsr_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    lsr_rule = Column(String(255), nullable=False)
    confidence = Column(Float, nullable=False)

    report = relationship("Report", back_populates="lsr_tags")


class BarrierFailure(Base):
    """
    Extracted physical/administrative safety barrier failures and critical evidence phrases.
    """
    __tablename__ = "barrier_failures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    barrier_type = Column(String(255), nullable=False) # e.g. "Energy Isolation", "Blowout Prevention", "Permit to Work"
    evidence_phrase = Column(Text, nullable=False)
    severity = Column(SQLEnum(BarrierSeverity, name="barrier_severity_enum"), nullable=False, default=BarrierSeverity.medium)

    report = relationship("Report", back_populates="barrier_failures")


class PrecursorPattern(Base):
    """
    Aggregated spatio-temporal precursor patterns identified across Oil India rigs/sites.
    """
    __tablename__ = "precursor_patterns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    activity = Column(String(255), nullable=False, index=True)
    location = Column(String(255), nullable=False, index=True)
    barrier_type = Column(String(255), nullable=False, index=True)
    occurrence_count = Column(Integer, nullable=False, default=1)
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    trend = Column(SQLEnum(PatternTrend, name="pattern_trend_enum"), nullable=False, default=PatternTrend.stable)


class SafetyIndex(Base):
    """
    Calculated safety index metrics per site/period (SIF density, recurrence score, SII score).
    """
    __tablename__ = "safety_index"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    period = Column(Date, nullable=False, index=True)
    sif_density = Column(Float, nullable=False, default=0.0)
    barrier_recurrence_score = Column(Float, nullable=False, default=0.0)
    sii_score = Column(Float, nullable=False, default=0.0) # Safety Improvement Index

    site = relationship("Site", back_populates="safety_indices")

    __table_args__ = (
        Index("ix_safety_index_site_period", "site_id", "period", unique=True),
    )


class ReviewQueue(Base):
    """
    Human-in-the-loop (HITL) review queue for low-confidence or borderline SIF precursor incidents.
    """
    __tablename__ = "review_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    resolved = Column(Boolean, nullable=False, default=False, index=True)
    corrected_label = Column(String(255), nullable=True)
    corrected_lsr = Column(String(255), nullable=True)

    report = relationship("Report", back_populates="review_queue_entries")
    assignee = relationship("User", back_populates="assigned_reviews", foreign_keys=[assigned_to])


class ModelFeedbackLog(Base):
    """
    Audit log for active learning and fine-tuning: captures human corrections against AI predictions.
    """
    __tablename__ = "model_feedback_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    original_label = Column(String(255), nullable=False)
    corrected_label = Column(String(255), nullable=False)
    corrected_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    report = relationship("Report", back_populates="feedback_logs")
    feedback_user = relationship("User", back_populates="feedback_logs", foreign_keys=[corrected_by])


class Alert(Base):
    """
    Real-time notifications sent to HSE officers and Rig Superintendents for critical SIF signals.
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type = Column(String(100), nullable=False) # e.g. "SMS", "Email", "In-App Push"
    sent_to = Column(String(255), nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    acknowledged = Column(Boolean, nullable=False, default=False, index=True)

    report = relationship("Report", back_populates="alerts")


class AuditLog(Base):
    """
    System-wide immutable audit trail of critical actions and data mutations.
    """
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    action = Column(String(100), nullable=False) # CREATE, UPDATE, DELETE, OVERRIDE, APPROVE
    actor = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    before = Column(JSON, nullable=True)
    after = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    actor_user = relationship("User", back_populates="audit_logs", foreign_keys=[actor])


class CaseLibrary(Base):
    """
    Safety Memory feature: historical fatality and severe incident case library
    used for RAG similarity matching and precursor learning.
    """
    __tablename__ = "case_library"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    incident_year = Column(Integer, nullable=False)
    operation_type = Column(String(100), nullable=False) # Drilling, Workover, Production, Pipeline, Refinery
    lsr_category = Column(String(150), nullable=False, index=True) # e.g. "Energy Isolation", "Line of Fire", "Confined Space"
    failed_barriers = Column(JSON, nullable=True) # list of barrier descriptions
    root_causes = Column(Text, nullable=False)
    lessons_learned = Column(Text, nullable=False)
    embedding = Column(SafeVector(384), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ColumnMappingTemplate(Base):
    """
    Stores confirmed spreadsheet column mapping configurations per format fingerprint
    so re-uploads of the same format automatically resolve without manual mapping.
    """
    __tablename__ = "column_mapping_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fingerprint = Column(String(255), unique=True, index=True, nullable=False)
    source_name = Column(String(255), nullable=True)
    mapping = Column(JSON, nullable=False) # { "target_field": "Actual Column Name" }
    column_headers = Column(JSON, nullable=False) # List of original column names
    sample_preview = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


