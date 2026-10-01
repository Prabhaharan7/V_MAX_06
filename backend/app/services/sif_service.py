from typing import List, Optional
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.safety_report import SafetyReport
from app.schemas.safety_report import SafetyReportCreate, SafetyReportStats, SIFAnalysisResult
from app.ml.precursor_detector import detector


class SIFService:
    @staticmethod
    def analyze_text(title: str, description: str) -> SIFAnalysisResult:
        analysis = detector.analyze_report(title, description)
        return SIFAnalysisResult(**analysis)

    @staticmethod
    async def create_report(db: AsyncSession, report_in: SafetyReportCreate) -> SafetyReport:
        analysis = detector.analyze_report(report_in.title, report_in.description)
        embedding = detector.generate_dummy_embedding(f"{report_in.title} {report_in.description}")

        db_report = SafetyReport(
            title=report_in.title,
            description=report_in.description,
            location=report_in.location,
            report_type=report_in.report_type,
            reported_by=report_in.reported_by,
            is_sif_precursor=analysis["is_sif_precursor"],
            sif_confidence=analysis["sif_confidence"],
            precursor_category=analysis["precursor_category"],
            risk_level=analysis["risk_level"],
            ai_analysis_summary=analysis["ai_analysis_summary"],
            embedding=embedding,
        )
        db.add(db_report)
        await db.commit()
        await db.refresh(db_report)
        return db_report

    @staticmethod
    async def get_reports(
        db: AsyncSession, skip: int = 0, limit: int = 50, sif_only: Optional[bool] = None
    ) -> List[SafetyReport]:
        stmt = select(SafetyReport).order_by(desc(SafetyReport.created_at)).offset(skip).limit(limit)
        if sif_only is not None:
            stmt = stmt.where(SafetyReport.is_sif_precursor == sif_only)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_stats(db: AsyncSession) -> SafetyReportStats:
        total_stmt = select(func.count(SafetyReport.id))
        sif_stmt = select(func.count(SafetyReport.id)).where(SafetyReport.is_sif_precursor == True)
        high_risk_stmt = select(func.count(SafetyReport.id)).where(
            SafetyReport.risk_level.in_(["High", "Critical"])
        )

        total_reports = (await db.execute(total_stmt)).scalar() or 0
        sif_count = (await db.execute(sif_stmt)).scalar() or 0
        high_risk_count = (await db.execute(high_risk_stmt)).scalar() or 0
        percentage = round((sif_count / total_reports * 100), 1) if total_reports > 0 else 0.0

        return SafetyReportStats(
            total_reports=total_reports,
            sif_precursors_detected=sif_count,
            high_critical_risk_count=high_risk_count,
            sif_percentage=percentage,
        )


sif_service = SIFService()
