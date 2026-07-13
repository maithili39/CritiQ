"""Shared rate limiter instance, imported by main.py (to attach to the app) and by
routers (to decorate individual endpoints) — avoids a circular import between the two.

Storage: Redis when REDIS_URL is set, otherwise slowapi's in-memory default. In-memory
is fine for a single backend process (local dev, one container) but each replica would
enforce its own separate limit if you scale horizontally — a caller could get roughly
N times the intended rate across N replicas. REDIS_URL makes the limit shared and
accurate once you run more than one backend instance."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL or None,
)
