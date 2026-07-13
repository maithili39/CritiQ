"""Shared FastAPI dependencies for authenticated routes."""

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
    if not settings.ADMIN_API_KEY:
        raise HTTPException(503, "Admin endpoints are disabled until ADMIN_API_KEY is configured.")

    if not secrets.compare_digest(admin_api_key, settings.ADMIN_API_KEY):
        raise HTTPException(403, "Invalid admin API key.")
