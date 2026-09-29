"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Unknown environment variables are never collected, but every key in the
        # dotenv file is — so a single line meant for something else fails the whole
        # model and the app dies at import, before main.py runs a line of its own.
        # `scripts/seed_combine.py` reads BSAMS_REHEARSAL_EMAIL from the environment
        # and `.env` is where it is documented to live, beside the Supabase values
        # this class does want.
        extra="ignore",
    )

    # Supabase Configuration
    supabase_url: str = ""
    supabase_key: str = ""

    # API Settings
    api_v1_prefix: str = "/api/v1"

    # Logging
    log_level: str = "INFO"

    # Environment
    environment: str = "production"

    # Frontend URL (for password reset redirect links etc.)
    frontend_url: str = ""


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
