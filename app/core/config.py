from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Void Excel"
    debug: bool = False

    # No credentials in code: must be provided via environment.
    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    storage_dir: str = "storage"
    template_path: str = "templates/certificate_template.pdf"
    max_recipients_per_job: int = 5000


@lru_cache
def get_settings() -> Settings:
    return Settings()
