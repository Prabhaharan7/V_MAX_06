from datetime import datetime
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., example="ok")
    app_name: str = Field(..., example="SIF Sentinel AI")
    version: str = Field(default="1.0.0", example="1.0.0")
    timestamp: datetime
    database: str = Field(..., example="connected")
    environment: str = Field(..., example="development")
