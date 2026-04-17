"""Redis-backed sliding window rate limiter."""
import time
from fastapi import HTTPException

from app.config import settings


def check_rate_limit(redis_client, user_id: str) -> None:
    """
    Enforce per-user request limit over the last 60 seconds.
    """
    now = int(time.time())
    window_start = now - 60
    key = f"rate:{user_id}"

    pipe = redis_client.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    pipe.zadd(key, {str(now): now})
    pipe.expire(key, 61)
    _, current_count, _, _ = pipe.execute()

    if int(current_count) >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": settings.rate_limit_per_minute,
                "window_seconds": 60,
            },
        )
