from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


def validate_database_url(url: str) -> None:
    """Raise a helpful error when .env still has the example placeholder."""
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if hostname in {"host", "your-neon-host.neon.tech", "dbname", "your-neon-host"}:
        raise RuntimeError(
            "DATABASE_URL is still a placeholder in backend/.env.\n"
            "Set up a free Postgres database and paste the real connection string:\n"
            "  1. Go to https://neon.tech and create a free project\n"
            "  2. Copy the connection string (pooled, with ?sslmode=require)\n"
            "  3. Replace DATABASE_URL in backend/.env\n"
            "  4. Run: alembic upgrade head"
        )
    if not parsed.scheme.startswith("postgres"):
        raise RuntimeError(
            f"DATABASE_URL must be a PostgreSQL URL (postgresql://...). Got scheme: {parsed.scheme!r}"
        )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/study_planner"

    # Auth
    JWT_SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # LLM
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_FAST_MODEL: str = "llama-3.1-8b-instant"  # batched quiz generation

    # YouTube
    YOUTUBE_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: str = "*"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
validate_database_url(settings.DATABASE_URL)
