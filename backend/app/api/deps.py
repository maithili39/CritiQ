"""Shared FastAPI dependencies for authenticated routes."""

import hashlib
import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.session import InterviewSession
from app.models.user import User


def get_current_user(
    authorization: str = Header(..., description="Bearer <access token>"),
    db: DBSession = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or malformed Authorization header.")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid or expired token.")

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(401, "User not found.")
    return user


def get_session_by_access_token(
    session_id: str,
    token: str,
    db: DBSession = Depends(get_db),
) -> InterviewSession:
    """
    Candidate-side equivalent of `require_owned_session`: instead of a logged-in
    user, the caller proves access with the per-session invite token (?token=...).
    Same 404-either-way behavior — a wrong/missing token can't distinguish "not
    yours" from "doesn't exist."
    """
    session = db.query(InterviewSession).filter_by(id=session_id).first()
    if not session or not secrets.compare_digest(token, session.access_token):
        raise HTTPException(404, f"Session {session_id} not found")
    return session


def require_admin_api_key(
    admin_api_key: str = Header(default="", alias="X-Admin-API-Key"),
) -> None:
    """
    Validates the incoming X-Admin-API-Key header in constant time.

    Two storage modes — ADMIN_API_KEY_HASH takes precedence:

      ADMIN_API_KEY_HASH (preferred):
        Store only the SHA-256 hex-digest of your chosen key. The raw key never
        enters the running process. To rotate: pick a new key, hash it, update the
        env var (no code change, no deploy needed beyond restarting the service).
        Generate:  echo -n 'myrawkey' | sha256sum

      ADMIN_API_KEY (legacy):
        The plaintext key lives in the env var. Works fine for simple setups, but
        means the raw secret is visible in process env dumps / platform dashboards.

    If neither is set the endpoint returns 503 (disabled), not 403.
    """
    has_hash = bool(settings.ADMIN_API_KEY_HASH)
    has_plain = bool(settings.ADMIN_API_KEY)

    if not has_hash and not has_plain:
        raise HTTPException(503, "Admin endpoints are disabled until ADMIN_API_KEY is configured.")

    if has_hash:
        # Hash the incoming key and compare digests — constant-time, raw key never stored.
        incoming_hash = hashlib.sha256(admin_api_key.encode("utf-8")).hexdigest()
        if not secrets.compare_digest(incoming_hash, settings.ADMIN_API_KEY_HASH):
            raise HTTPException(403, "Invalid admin API key.")
    else:
        # Legacy plaintext comparison — still constant-time via secrets.compare_digest.
        if not secrets.compare_digest(admin_api_key, settings.ADMIN_API_KEY):
            raise HTTPException(403, "Invalid admin API key.")
