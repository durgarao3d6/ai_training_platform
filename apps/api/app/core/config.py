"""Application settings, read from environment variables (Architecture 18.2)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # API connects as the non-owner role (RLS applies). Migrations and seed use the owner.
    database_url: str = "postgresql+psycopg://aitms_app:change-me-app@postgres:5432/aitms"
    migration_database_url: str = "postgresql+psycopg://aitms:change-me-local@postgres:5432/aitms"
    redis_url: str = "redis://redis:6379/0"
    s3_endpoint: str = "http://s3:9000"
    s3_bucket: str = "aitms"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"
    # Where the browser posts uploads: the web app's same-origin proxy to the S3 endpoint.
    s3_public_upload_url: str = "/s3"

    # Submissions (task 4.1, 4.2)
    max_upload_bytes: int = 25 * 1024 * 1024
    upload_url_ttl_seconds: int = 600
    max_text_chars: int = 50_000
    link_check_timeout_seconds: float = 5.0
    llm_provider: str = "openai"
    llm_mode: str = "fixture"  # live | fixture
    # Live calls are refused unless the organisation has approved data handling (open decision 8).
    llm_live_approved: bool = False
    openai_api_key: str = ""  # secret: set in .env only, never committed
    llm_model: str = "gpt-4o-mini"  # change in .env; recorded on every llm_call
    # Feature flag for AI-assisted authoring (open question A1). Off by default.
    ai_authoring_enabled: bool = False
    content_dir: str = "/content"  # mounted read-only in compose; tests override via CONTENT_DIR
    sandbox_url: str = "http://sandbox-runner:8100"
    reference_app_url: str = "http://reference-app:8200"

    # Auth (Architecture 13.1). JWT_SECRET has no default on purpose.
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7
    cookie_secure: bool = True  # set COOKIE_SECURE=false only for local http
    login_max_failures: int = 5
    lockout_minutes: int = 15
    auth_rate_limit_per_minute: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
