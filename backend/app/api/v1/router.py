from fastapi import APIRouter
from app.api import alerts, forecast, model_feedback, patterns, review_queue, sites
from app.api.v1.endpoints import auth, health, reports

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & RBAC"])
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(reports.router, prefix="/reports", tags=["Safety Reports & Ingestion"])
api_router.include_router(patterns.router, prefix="/patterns", tags=["Precursor Patterns & Site Ranking"])
api_router.include_router(review_queue.router, prefix="/review-queue", tags=["Active Learning Review Queue"])
api_router.include_router(model_feedback.router, prefix="/model", tags=["Model Feedback & Active Learning Stats"])
api_router.include_router(sites.router, prefix="/sites", tags=["Operational Sites & Safety Improvement Index"])
api_router.include_router(forecast.router, prefix="/forecast", tags=["Predictive Risk Heatmap & 30-Day Forecast"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Real-Time Precursor Alerts"])
