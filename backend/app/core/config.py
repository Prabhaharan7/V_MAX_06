from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    PROJECT_NAME: str = "SIF Sentinel AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Database Settings (defaults to local SQLite if PostgreSQL is not active)
    DATABASE_URL: str = "sqlite+aiosqlite:///./sif_sentinel.db"

    # Security Settings
    JWT_SECRET: str = "sif_sentinel_super_secret_jwt_key_sih2026_ps26165_oil_india"
    JWT_EXPIRY: int = 1440  # In minutes
    ALGORITHM: str = "HS256"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return ["*"]

    # ML Precursor Classifier Settings
    MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    SIF_CONFIDENCE_THRESHOLD: float = 0.75


settings = Settings()
