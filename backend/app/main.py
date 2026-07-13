import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if settings.SECURITY_HSTS_SECONDS > 0:
        response.headers["Strict-Transport-Security"] = (
            f"max-age={settings.SECURITY_HSTS_SECONDS}; includeSubDomains"
        )
    return response

app.include_router(auth.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(candidate.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}
