import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings, validate_cors_origins
from app.core.limiter import limiter
from app.core.logging import configure_logging
from app.api import auth, sessions, admin, candidate

configure_logging()
logger = logging.getLogger(__name__)

if settings.SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
    )
    logger.info("Sentry error tracking enabled")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is managed by Alembic migrations (run `alembic upgrade head` before starting).
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered role-based candidate screening system with RAG pipeline.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

validate_cors_origins(settings.allowed_origins_list, settings.DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Swagger UI (/docs) and ReDoc (/redoc) load their JS/CSS from a CDN and inline
# script - a strict CSP would break them. Everything else on this API only ever
# returns JSON, so 'none' is safe and isn't a meaningful UX cost anywhere else.
_CSP_EXEMPT_PATHS = {"/docs", "/redoc", "/openapi.json"}


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path not in _CSP_EXEMPT_PATHS:
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    if settings.SECURITY_HSTS_SECONDS > 0:
        response.headers["Strict-Transport-Security"] = (
            f"max-age={settings.SECURITY_HSTS_SECONDS}; includeSubDomains"
        )
    return response


@app.middleware("http")
async def log_request_timing(request: Request, call_next):
    """
    Without this, there was no visibility into which stage of an interview is
    slow - only "the whole request took N seconds" (or nothing at all, since
    Sentry's traces_sample_rate defaults to 10%, not every request). This logs
    every request's latency; slow ones (>3s) log at WARNING so they stand out
    in dashboards/alerts without configuring a separate APM tool.
    """
    start = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)

    log_fn = logger.warning if duration_ms > 3000 else logger.info
    log_fn(
        "%s %s -> %d in %sms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra={"duration_ms": duration_ms, "path": request.url.path, "status_code": response.status_code},
    )
    response.headers["X-Response-Time-Ms"] = str(duration_ms)
    return response

app.include_router(auth.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(candidate.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}
