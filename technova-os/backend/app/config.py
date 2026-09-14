"""Application configuration (12-factor: everything via env)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TECHNOVA_", env_file=".env", extra="ignore")

    app_name: str = "TECHNOVA OS"
    environment: str = "development"
    # SECURITY: override in production via TECHNOVA_SECRET_KEY
    secret_key: str = "dev-insecure-change-me-in-production-please-0123456789"
    qr_secret: str = "dev-qr-secret-change-me-in-production-abcdef"
    access_token_expire_minutes: int = 60 * 12
    database_url: str = "sqlite:///./technova.db"
    # Daily point caps per category to prevent farming
    daily_cap_learning: int = 200
    daily_cap_attendance: int = 60
    daily_cap_social: int = 150
    qr_window_seconds: int = 90


@lru_cache
def get_settings() -> Settings:
    return Settings()
