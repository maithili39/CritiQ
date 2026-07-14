import re
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import and_
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import (
    create_access_token,
    generate_urlsafe_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import User
from app.services.emailer import send_text_email

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


class Credentials(BaseModel):
    email: str
    password: str


class EmailOnlyPayload(BaseModel):
    email: str


class TokenPasswordPayload(BaseModel):
    token: str
    password: str


class TokenOnlyPayload(BaseModel):
    token: str


def _utcnow() -> datetime:
    # Naive UTC — the User.locked_until / *_token_expires_at columns are plain DateTime
    # (no tz), so SQLAlchemy hands back naive datetimes on read. Comparing an aware "now"
    # against those raises `TypeError: can't compare offset-naive and offset-aware
    # datetimes`, so this strips tzinfo rather than using datetime.utcnow() (deprecated).
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(400, f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")


def _issue_email_verification_token(user: User) -> str:
    token = generate_urlsafe_token()
    user.email_verification_token_hash = hash_token(token)
    user.email_verification_token_expires_at = _utcnow() + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)
    return token


def _issue_password_reset_token(user: User) -> str:
    token = generate_urlsafe_token()
    user.password_reset_token_hash = hash_token(token)
    user.password_reset_token_expires_at = _utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    return token


def _send_email_verification(email: str, token: str) -> None:
    link = f"{settings.APP_BASE_URL.rstrip('/')}/verify-email?token={token}"
    body = (
        "Please verify your email address.\n\n"
        f"Verification link: {link}\n\n"
        f"If the link is not clickable, use this token: {token}\n"
    )
    send_text_email(to_email=email, subject="Verify your email", body=body)


def _send_password_reset(email: str, token: str) -> None:
    link = f"{settings.APP_BASE_URL.rstrip('/')}/reset-password?token={token}"
    body = (
        "A password reset was requested for your account.\n\n"
        f"Reset link: {link}\n\n"
        f"If the link is not clickable, use this token: {token}\n"
        "If you did not request this, you can ignore this message.\n"
    )
    send_text_email(to_email=email, subject="Password reset", body=body)


@router.post("/register", response_model=dict)
@limiter.limit("5/minute")
def register(request: Request, payload: Credentials, db: DBSession = Depends(get_db)):
    email = _normalize_email(payload.email)
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Invalid email address.")
    _validate_password(payload.password)

    if db.query(User).filter_by(email=email).first():
        raise HTTPException(409, "An account with this email already exists.")

    user = User(email=email, password_hash=hash_password(payload.password))
    verification_token = _issue_email_verification_token(user)
    db.add(user)
    db.commit()
    db.refresh(user)

    _send_email_verification(user.email, verification_token)

    if settings.FORCE_EMAIL_VERIFICATION:
        return {
            "message": "Registration successful. Please verify your email before logging in.",
            "email": user.email,
            "email_verified": user.email_verified,
        }

    return {
        "access_token": create_access_token(user.id),
        "email": user.email,
        "email_verified": user.email_verified,
    }


@router.post("/login", response_model=dict)
@limiter.limit("10/minute")
def login(request: Request, payload: Credentials, db: DBSession = Depends(get_db)):
    email = _normalize_email(payload.email)
    now = _utcnow()
    user = db.query(User).filter_by(email=email).first()

    if user and user.locked_until and user.locked_until > now:
        raise HTTPException(423, "Account is temporarily locked. Please try again later.")

    if not user or not verify_password(payload.password, user.password_hash):
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= settings.AUTH_MAX_FAILED_ATTEMPTS:
                user.failed_login_attempts = 0
                user.locked_until = now + timedelta(minutes=settings.AUTH_LOCKOUT_MINUTES)
            db.commit()
        raise HTTPException(401, "Incorrect email or password.")

    if settings.FORCE_EMAIL_VERIFICATION and not user.email_verified:
        raise HTTPException(403, "Please verify your email before logging in.")

    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    return {
        "access_token": create_access_token(user.id),
        "email": user.email,
        "email_verified": user.email_verified,
    }


@router.get("/me", response_model=dict)
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "email_verified": current_user.email_verified,
    }


@router.post("/password-reset/request", response_model=dict)
@limiter.limit("5/minute")
def request_password_reset(request: Request, payload: EmailOnlyPayload, db: DBSession = Depends(get_db)):
    email = _normalize_email(payload.email)
    if EMAIL_RE.match(email):
        user = db.query(User).filter_by(email=email).first()
        if user:
            token = _issue_password_reset_token(user)
            db.commit()
            _send_password_reset(user.email, token)

    return {
        "message": "If that account exists, a password reset email has been sent.",
    }


@router.post("/password-reset/confirm", response_model=dict)
@limiter.limit("10/minute")
def confirm_password_reset(request: Request, payload: TokenPasswordPayload, db: DBSession = Depends(get_db)):
    _validate_password(payload.password)
    token_hash = hash_token(payload.token.strip())
    now = _utcnow()

    user = db.query(User).filter(
        and_(
            User.password_reset_token_hash == token_hash,
            User.password_reset_token_expires_at.is_not(None),
            User.password_reset_token_expires_at > now,
        )
    ).first()
    if not user:
        raise HTTPException(400, "Invalid or expired password reset token.")

    user.password_hash = hash_password(payload.password)
    user.password_reset_token_hash = None
    user.password_reset_token_expires_at = None
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    return {"message": "Password updated successfully."}


@router.post("/verify-email/request", response_model=dict)
@limiter.limit("5/minute")
def request_email_verification(request: Request, payload: EmailOnlyPayload, db: DBSession = Depends(get_db)):
    email = _normalize_email(payload.email)
    if EMAIL_RE.match(email):
        user = db.query(User).filter_by(email=email).first()
        if user and not user.email_verified:
            token = _issue_email_verification_token(user)
            db.commit()
            _send_email_verification(user.email, token)

    return {
        "message": "If that account exists, an email verification message has been sent.",
    }


@router.post("/verify-email/confirm", response_model=dict)
@limiter.limit("10/minute")
def confirm_email_verification(request: Request, payload: TokenOnlyPayload, db: DBSession = Depends(get_db)):
    token_hash = hash_token(payload.token.strip())
    now = _utcnow()

    user = db.query(User).filter(
        and_(
            User.email_verification_token_hash == token_hash,
            User.email_verification_token_expires_at.is_not(None),
            User.email_verification_token_expires_at > now,
        )
    ).first()
    if not user:
        raise HTTPException(400, "Invalid or expired email verification token.")

    user.email_verified = True
    user.email_verification_token_hash = None
    user.email_verification_token_expires_at = None
    db.commit()

    return {"message": "Email verified successfully."}
