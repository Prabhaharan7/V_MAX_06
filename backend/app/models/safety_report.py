from sqlalchemy import Boolean, Column, Float, String, Text
from pgvector.sqlalchemy import Vector
from app.models.base import TimeStampedModel


class SafetyReport(TimeStampedModel):
    __tablename__ = "safety_reports"

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String(255), nullable=False, default="Oil Field / Facility")
    report_type = Column(String(100), nullable=False, default="Near Miss") # Near Miss, Unsafe Act, Unsafe Condition, Hazard
    reported_by = Column(String(255), nullable=True, default="Field Safety Officer")
    
    # AI/NLP Precursor Evaluation Fields
    is_sif_precursor = Column(Boolean, default=False, nullable=False, index=True)
    sif_confidence = Column(Float, default=0.0, nullable=False)
    precursor_category = Column(String(150), nullable=True, index=True)
    risk_level = Column(String(50), nullable=False, default="Low", index=True) # Low, Medium, High, Critical
    ai_analysis_summary = Column(Text, nullable=True)

    # 384-dimensional vector embedding (for sentence-transformers like all-MiniLM-L6-v2)
    embedding = Column(Vector(384), nullable=True)
