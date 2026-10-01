from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import alerts, datasets, forecast, model_feedback, patterns, reports, review_queue, sites
from app.api.v1.endpoints import auth
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.schemas.health import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure pgvector and tables exist
    async with engine.begin() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        except Exception as e:
            pass
        await conn.run_sync(Base.metadata.create_all)
        for col_def in [
            "raw_metadata JSON",
            "upload_batch_id VARCHAR(100)",
            "upload_batch_label VARCHAR(255)",
            "ground_truth_sif_label VARCHAR(50)",
            "ground_truth_lsr VARCHAR(255)",
            "ground_truth_barrier_status VARCHAR(255)",
            "ground_truth_split VARCHAR(50)",
        ]:
            try:
                await conn.execute(text(f"ALTER TABLE reports ADD COLUMN {col_def};"))
            except Exception:
                pass

    # Check if database needs initial seeding
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.entities import User
        from sqlalchemy import select, func

        async with AsyncSessionLocal() as session:
            user_count = (await session.execute(select(func.count(User.id)))).scalar() or 0
            if user_count == 0:
                print("⚡ Auto-seeding initial dataset for SIF Sentinel AI (SIH 2026 PS 26165)...")
                from scripts.seed_data import seed_database
                await seed_database()
    except Exception as e:
        print(f"Startup seeding check: {e}")

    yield
    # Shutdown: Dispose engine
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="SIF Sentinel AI - Serious Injury & Fatality (SIF) Precursor NLP & AI Intelligence Engine for Oil India (SIH 2026 PS 26165)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["General"])
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "description": "Oil India SIF Precursor Detection AI Engine (SIH 2026 PS 26165)",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
        "endpoints": {
            "auth": "/api/auth",
            "reports": "/api/reports",
            "patterns": "/api/patterns",
            "ranked_sites": "/api/patterns/ranked-sites",
        },
    }


# Health check endpoint accessible at /api/health
@app.get("/api/health", response_model=HealthResponse, tags=["Health"], summary="Health Check")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "connected"
    try:
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


# Direct Auth router mount at /api/auth
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication & RBAC"])

# Direct Reports router mount at /api/reports
app.include_router(reports.router, prefix="/api/reports", tags=["Safety Reports & Ingestion"])

# Direct Patterns router mount at /api/patterns
app.include_router(patterns.router, prefix="/api/patterns", tags=["Precursor Patterns & Site Ranking"])

# Direct Review Queue router mount at /api/review-queue
app.include_router(review_queue.router, prefix="/api/review-queue", tags=["Active Learning Review Queue"])

# Direct Model Feedback & Stats router mount at /api/model
app.include_router(model_feedback.router, prefix="/api/model", tags=["Model Feedback & Active Learning Stats"])

# Direct Sites router mount at /api/sites
app.include_router(sites.router, prefix="/api/sites", tags=["Operational Sites & Safety Improvement Index"])

# Direct Forecast Heatmap router mount at /api/forecast
app.include_router(forecast.router, prefix="/api/forecast", tags=["Predictive Risk Heatmap & 30-Day Forecast"])

# Direct Alerts router mount at /api/alerts
app.include_router(alerts.router, prefix="/api/alerts", tags=["Real-Time Precursor Alerts"])

# Direct Datasets & Accuracy Benchmark router mount at /api/datasets
app.include_router(datasets.router, prefix="/api/datasets", tags=["Dataset Accuracy & Model Evaluation Benchmark"])

# Include full API v1 routers (/api/v1/...)
app.include_router(api_router, prefix=settings.API_V1_STR)
