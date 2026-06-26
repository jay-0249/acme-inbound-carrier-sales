from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    LOADS_API_KEY: str
    FMCSA_API_KEY: str
    DATABASE_URL: str = "sqlite+aiosqlite:///./carrier_sales.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
