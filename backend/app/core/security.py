from fastapi import Depends, Header, HTTPException

from app.core.config import Settings, get_settings


async def verify_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> str:
    if not x_api_key or x_api_key != settings.LOADS_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key
