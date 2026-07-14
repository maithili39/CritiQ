from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


def normalize_database_url(url: str) -> str:
    """
    Managed Postgres providers (e.g. Render) hand out connection strings as plain
    "postgresql://...", which SQLAlchemy resolves to the psycopg2 dialect by default.
    Only psycopg v3 is installed (see requirements.txt), so normalize the scheme here
    rather than adding a second, redundant driver dependency just to satisfy the default.
    Used by both the app's engine (below) and alembic/env.py's migration engine.
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


engine = create_engine(normalize_database_url(settings.DATABASE_URL), pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
