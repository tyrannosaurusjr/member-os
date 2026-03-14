from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/member_os"
    SYNC_DATABASE_URL: str = "postgresql://user:password@localhost:5432/member_os"
    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str = "dev-secret-key"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/callback"

    # Connectors
    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    MAILCHIMP_API_KEY: str = ""
    MAILCHIMP_SERVER_PREFIX: str = "us1"
    LUMA_API_KEY: str = ""
    GOOGLE_SERVICE_ACCOUNT_JSON: str = ""

    # Identity resolution thresholds
    AUTO_MERGE_THRESHOLD: float = 95.0
    REVIEW_THRESHOLD: float = 75.0

    # Price anomaly threshold (fraction of list price)
    PRICE_ANOMALY_THRESHOLD: float = 0.30


settings = Settings()
