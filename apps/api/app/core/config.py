from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SECRET = "dev-secret-key-replace-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────
    api_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    secret_key: str = _DEV_SECRET

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_changed_in_production(cls, v: str, info) -> str:
        """Fail loudly if the default dev secret is used in production."""
        # We can't access other fields at validation time via info.data reliably,
        # so we check at property access level instead — see is_production check below.
        return v

    # ── Database ───────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://copilot:changeme@localhost:5432/cloud_posture"
    )

    # ── Auth ───────────────────────────────────────────────────
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # ── AWS (Phase 3 — bootstrap credentials for cross-account STS) ───
    # Use IAM role in production (leave blank); use access key for local dev.
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_default_region: str = "us-east-1"
    # STS session duration for assumed roles (seconds, max 43200 = 12h)
    aws_sts_session_duration: int = 3600

    # ── Redis (production rate limiting / job queue) ──────────
    # Leave blank to use in-memory fallback (dev/test only)
    redis_url: str = ""

    # ── AI (Phase 6) ───────────────────────────────────────────
    ai_provider: str = "anthropic"
    anthropic_api_key: str = ""
    ai_model: str = "claude-sonnet-4-6"
    ai_max_tokens: int = 1024
    ai_enabled: bool = True

    # ── Email (SMTP) ────────────────────────────────────────────────
    # Leave blank to disable email (dev/test). Set all fields for production.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@cloudposture.io"
    smtp_from_name: str = "Cloud Posture Copilot"
    smtp_use_tls: bool = True

    @property
    def email_enabled(self) -> bool:
        """True only when SMTP host is configured."""
        return bool(self.smtp_host)

    @property
    def is_production(self) -> bool:
        return self.api_env == "production"

    @property
    def is_development(self) -> bool:
        return self.api_env == "development"

    def assert_production_secrets(self) -> None:
        """Call during app startup in production to fail fast on insecure defaults."""
        if self.is_production and self.secret_key == _DEV_SECRET:
            raise RuntimeError(
                "SECRET_KEY must be overridden in production. "
                "Set the SECRET_KEY environment variable to a cryptographically "
                "random 32+ character string."
            )


settings = Settings()
