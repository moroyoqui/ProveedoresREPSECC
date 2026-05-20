"""Centralized application settings loaded from environment variables."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import Field, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PROD = "prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_env: AppEnv = AppEnv.LOCAL
    app_secret: SecretStr
    app_base_url: str = "http://localhost:8000"
    upload_root: Path = Path("/var/repse/uploads")
    log_level: str = "INFO"

    # Database
    db_host: str = "mysql"
    db_port: int = 3306
    db_name: str = "repse"
    db_user: str = "repse"
    db_pass: SecretStr

    # OIDC
    oidc_google_client_id: str = ""
    oidc_google_client_secret: SecretStr = SecretStr("")
    oidc_microsoft_client_id: str = ""
    oidc_microsoft_client_secret: SecretStr = SecretStr("")
    oidc_microsoft_tenant: str = "common"

    # OCR
    tesseract_lang: str = "spa+eng"

    # Observability
    sentry_dsn: str = ""
    prometheus_enabled: bool = True

    # Limits
    upload_max_bytes: int = 25 * 1024 * 1024  # 25 MiB (FR-010 spec 001)
    download_token_ttl_seconds: int = 300  # 5 min (research.md §5 spec 001)
    expiring_soon_default_days: int = 15  # FR-013 spec 001

    rate_limit_auth_per_min: int = Field(default=10, ge=1)
    rate_limit_uploads_per_min: int = Field(default=60, ge=1)

    # Document deletion grace window (FR / contract spec 001).
    document_delete_grace_hours: int = Field(default=24, ge=0)

    # Background jobs
    documents_recalc_enabled: bool = True
    documents_recalc_hour_utc: int = Field(default=5, ge=0, le=23)  # ~23:00 CST

    @field_validator("app_secret")
    @classmethod
    def _validate_secret_length(cls, v: SecretStr, info: ValidationInfo) -> SecretStr:
        if len(v.get_secret_value()) < 16:
            raise ValueError("APP_SECRET must be at least 16 characters")
        return v

    @property
    def db_url(self) -> str:
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_pass.get_secret_value())
        return (
            f"mysql+pymysql://{user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    @property
    def is_local(self) -> bool:
        return self.app_env is AppEnv.LOCAL


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
