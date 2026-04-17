"""Monthly per-user budget guard using Redis."""
from datetime import datetime, timezone

from app.config import settings


def check_budget(redis_client, user_id: str, estimated_cost: float) -> None:
    """
    Raise HTTPException(402) when user exceeds monthly budget.
    """
    from fastapi import HTTPException

    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"

    current = float(redis_client.get(key) or 0.0)
    if current + estimated_cost > settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Monthly budget exceeded",
                "used_usd": round(current, 6),
                "budget_usd": settings.monthly_budget_usd,
                "month": month_key,
            },
        )


def record_spending(redis_client, user_id: str, cost_usd: float) -> float:
    """Persist monthly spend and return updated total."""
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"

    updated = float(redis_client.incrbyfloat(key, cost_usd))
    redis_client.expire(key, 32 * 24 * 3600)
    return round(updated, 6)
