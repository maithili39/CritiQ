from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


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
    ADMIN_API_KEY: str = ""
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
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
