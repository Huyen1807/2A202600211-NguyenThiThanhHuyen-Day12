"""Authentication helpers for API key protected endpoints."""
from fastapi import Header, HTTPException

from app.config import settings


def verify_api_key(x_api_key: str = Header(default="", alias="X-API-Key")) -> str:
    """
    Validate API key and return a stable user identifier for downstream checks.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include header: X-API-Key: <key>",
        )

    if x_api_key != settings.agent_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Lab scope: single shared API key maps to one logical user.
    return "api-key-user"
