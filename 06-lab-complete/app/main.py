"""Production AI Agent (Lab 06 complete)."""
import json
import logging
import signal
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, record_spending
from app.rate_limiter import check_rate_limit
from utils.mock_llm import ask as llm_ask

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0
_in_flight_requests = 0

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


def _estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    input_cost = (input_tokens / 1000) * 0.00015
    output_cost = (output_tokens / 1000) * 0.0006
    return round(input_cost + output_cost, 6)


def _append_history(user_id: str, role: str, content: str) -> None:
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    key = f"history:{user_id}:{month_key}"
    item = json.dumps(
        {
            "role": role,
            "content": content,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
    )
    pipe = redis_client.pipeline()
    pipe.rpush(key, item)
    pipe.ltrim(key, -20, -1)
    pipe.expire(key, 32 * 24 * 3600)
    pipe.execute()


def _get_history(user_id: str) -> list[dict]:
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    key = f"history:{user_id}:{month_key}"
    raw = redis_client.lrange(key, 0, -1)
    return [json.loads(x) for x in raw]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _is_ready
    logger.info(
        json.dumps(
            {
                "event": "startup",
                "app": settings.app_name,
                "version": settings.app_version,
                "environment": settings.environment,
            }
        )
    )

    redis_client.ping()
    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))

    yield

    _is_ready = False
    timeout = 30
    waited = 0
    while _in_flight_requests > 0 and waited < timeout:
        time.sleep(1)
        waited += 1
    logger.info(json.dumps({"event": "shutdown", "waited_seconds": waited}))


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count, _in_flight_requests
    _request_count += 1
    _in_flight_requests += 1
    start = time.time()
    try:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if "server" in response.headers:
            del response.headers["server"]
        logger.info(
            json.dumps(
                {
                    "event": "request",
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ms": round((time.time() - start) * 1000, 1),
                }
            )
        )
        return response
    except Exception:
        _error_count += 1
        raise
    finally:
        _in_flight_requests -= 1


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    question: str
    answer: str
    model: str
    timestamp: str
    history_length: int


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.post("/ask", response_model=AskResponse)
async def ask_agent(
    body: AskRequest,
    request: Request,
    user_id: str = Depends(verify_api_key),
):
    check_rate_limit(redis_client, user_id)

    input_tokens = len(body.question.split()) * 2
    provisional_cost = _estimate_cost_usd(input_tokens, 0)
    check_budget(redis_client, user_id, provisional_cost)

    _append_history(user_id, "user", body.question)
    answer = llm_ask(body.question)

    output_tokens = len(answer.split()) * 2
    final_cost = _estimate_cost_usd(input_tokens, output_tokens)
    record_spending(redis_client, user_id, final_cost)
    _append_history(user_id, "assistant", answer)

    history_len = len(_get_history(user_id))

    logger.info(
        json.dumps(
            {
                "event": "agent_call",
                "client": str(request.client.host) if request.client else "unknown",
                "q_len": len(body.question),
                "history_len": history_len,
                "user_id": user_id,
            }
        )
    )

    return AskResponse(
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        timestamp=datetime.now(timezone.utc).isoformat(),
        history_length=history_len,
    )


@app.get("/history")
def get_history(user_id: str = Depends(verify_api_key)):
    return {"items": _get_history(user_id)}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def ready():
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Not ready")

    try:
        redis_client.ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Redis not ready: {exc}")

    return {"ready": True}


@app.get("/metrics")
def metrics(user_id: str = Depends(verify_api_key)):
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    spent = float(redis_client.get(f"budget:{user_id}:{month_key}") or 0.0)
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "monthly_cost_usd": round(spent, 6),
        "monthly_budget_usd": settings.monthly_budget_usd,
        "budget_used_pct": round((spent / settings.monthly_budget_usd) * 100, 2),
    }


def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))


signal.signal(signal.SIGTERM, _handle_signal)


if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
