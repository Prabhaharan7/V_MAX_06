from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Application Health Check")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint returning system status, database connection, and environment metadata.
    """
    db_status = "connected"
    try:
        # Quick DB ping
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        app_name=settings.PROJECT_NAME,
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        database=db_status,
        environment=settings.ENVIRONMENT,
    )
