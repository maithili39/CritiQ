import hashlib
import logging

from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # API
    APP_NAME: str = "CritiQ"
    DEBUG: bool = False

    # Anthropic
    ANTHROPIC_API_KEY: str

    # Claude model
    CLAUDE_MODEL: str = "claude-sonnet-5"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://screening:screening@localhost:5432/screening"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / "data" / "chroma")

    # Knowledge base
    KNOWLEDGE_BASE_DIR: str = str(BASE_DIR / "knowledge_base")

    # Embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # RAG
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    TOP_K_RETRIEVAL: int = 5

    # Interview
    MAX_QUESTIONS: int = 8

    # Auth
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    AUTH_MAX_FAILED_ATTEMPTS: int = 5
    AUTH_LOCKOUT_MINUTES: int = 15
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    FORCE_EMAIL_VERIFICATION: bool = False

    # Security
    #
    # APP_ENV: set to "production" on Render/any live deployment. Controls startup
    # security warnings and (in future) other prod-only hardening.
    APP_ENV: str = "development"

    # ADMIN_API_KEY — two storage modes (use one, not both):
    #
    #   ADMIN_API_KEY (legacy): the raw key is stored in the env var and compared
    #   directly. Simple, but the raw secret lives in the running process's env.
    #
    #   ADMIN_API_KEY_HASH (preferred): store only the SHA-256 hex-digest of the
    #   key here (e.g. `echo -n 'myrawkey' | sha256sum`). The raw key never enters
    #   the process — `require_admin_api_key` hashes the incoming header and compares
    #   digests, so rotation is a one-step env-var update with no code change.
    #
    # If both are set, ADMIN_API_KEY_HASH takes precedence.
    ADMIN_API_KEY: str = ""
    ADMIN_API_KEY_HASH: str = ""  # SHA-256 hex-digest of the admin key

    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # HSTS: set to 31536000 (1 year) in production on any HTTPS deployment.
    # Defaults to 0 (off) so local HTTP dev doesn't poison the browser's HSTS cache.
    SECURITY_HSTS_SECONDS: int = 0

    # Observability
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    LOG_JSON: bool = False

    # Rate limiting (shared storage across replicas; empty = in-memory, single-process only)
    REDIS_URL: str = ""

    # Email
    APP_BASE_URL: str = "http://localhost:3000"
    EMAIL_FROM: str = "noreply@example.com"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = str(BASE_DIR / ".env")
        extra = "ignore"


settings = Settings()


def startup_security_warnings() -> None:
    """
    Log actionable warnings for security-relevant misconfigurations that are safe
    in local dev but should be addressed before going live. Called from the
    FastAPI lifespan so the warnings are visible in every deploy's startup log.
    """
    if settings.APP_ENV != "production":
        return

    if not settings.ADMIN_API_KEY and not settings.ADMIN_API_KEY_HASH:
        logger.warning(
            "SECURITY: ADMIN_API_KEY / ADMIN_API_KEY_HASH is not set. "
            "Admin endpoints (/api/admin/*) are disabled (503) until configured. "
            "Set ADMIN_API_KEY_HASH to the SHA-256 digest of your chosen admin key."
        )

    if settings.SECURITY_HSTS_SECONDS == 0:
        logger.warning(
            "SECURITY: SECURITY_HSTS_SECONDS=0 — HSTS is disabled. "
            "Set to 31536000 (1 year) so browsers enforce HTTPS after the first visit. "
            "Only safe to skip if TLS is terminated upstream without HSTS."
        )

    if "*" in settings.allowed_origins_list:
        logger.warning(
            "SECURITY: ALLOWED_ORIGINS includes '*' in production — CORS is open to any origin. "
            "Set ALLOWED_ORIGINS to your exact frontend URL(s)."
        )


def hash_admin_key(raw_key: str) -> str:
    """Return the SHA-256 hex-digest of a raw admin key string."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def validate_cors_origins(origins: list[str], debug: bool) -> None:
    """
    CORSMiddleware combines allow_origins=["*"] with allow_credentials=True by
    echoing back whatever Origin the request sent - it doesn't send a literal
    "*". A "*" here doesn't relax CORS, it silently disables it entirely (any
    origin, with credentials) while looking restrictive in config. Loud failure
    in production; a warning is enough for local dev/DEBUG.
    """
    if "*" not in origins:
        return
    if debug:
        import logging
        logging.getLogger(__name__).warning(
            "ALLOWED_ORIGINS includes '*' - CORS is effectively disabled (any origin allowed)."
        )
        return
    raise RuntimeError(
        "ALLOWED_ORIGINS includes '*' with DEBUG=False. This does not restrict CORS to '*' - "
        "combined with credentials it allows any origin. Set ALLOWED_ORIGINS to your actual "
        "frontend origin(s) before running in production."
    )
