from fastapi import Depends, Header, HTTPException

from app.core.config import Settings, get_settings


async def verify_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> str:
    """Full-access dependency. Accepts LOADS_API_KEY only. Used on write endpoints."""
    if not x_api_key or x_api_key != settings.LOADS_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key


async def verify_read_access(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> str:
    """Read-only dependency. Accepts LOADS_API_KEY (full, superset) OR READ_API_KEY.
    If READ_API_KEY is unset, only LOADS_API_KEY is accepted — preserves local-dev
    and existing-test behaviour without requiring a migration step."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    if x_api_key == settings.LOADS_API_KEY:
        return x_api_key
    if settings.READ_API_KEY and x_api_key == settings.READ_API_KEY:
        return x_api_key
    raise HTTPException(status_code=401, detail="Invalid or missing API key")
