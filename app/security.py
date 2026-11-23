from fastapi import Header, HTTPException

from app.config import settings


def require_app_key(x_api_key: str | None = Header(default=None)) -> None:
    if not settings.app_api_key or x_api_key != settings.app_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
