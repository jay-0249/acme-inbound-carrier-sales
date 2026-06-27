from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    LOADS_API_KEY: str
    FMCSA_API_KEY: str
    # READ_API_KEY scopes the public dashboard key to read-only endpoints.
    # If unset, read endpoints fall back to accepting LOADS_API_KEY only
    # (preserves local-dev and test behaviour without migration).
    READ_API_KEY: str | None = None
    DATABASE_URL: str = "sqlite+aiosqlite:///./carrier_sales.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
