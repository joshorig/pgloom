from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PGLOOM_", env_file=".env", extra="ignore")

    database_url: str = "postgresql://localhost:5432/pgloom_dev"
    test_database_url: str = "postgresql://localhost:5432/pgloom_test"
    artifact_root: Path = Path(".local/artifacts")
    worker_id: str = "local-worker"
    default_lease_seconds: int = Field(default=300, ge=1)
    log_level: str = "INFO"


def get_settings() -> Settings:
    return Settings()
