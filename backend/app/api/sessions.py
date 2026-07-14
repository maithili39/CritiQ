import json
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session as DBSession
from typing import Optional

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.roles import ALLOWED_ROLES, ROLE_LABELS
from app.models.session import InterviewSession, SessionStatus
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.interview import AnswerSubmit
from app.services import interview_orchestrator as orchestrator
from app.services.emailer import send_text_email
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])

MAX_NAME_LENGTH = 200
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PDF_MAGIC = b"%PDF-"


def _invite_url(session: InterviewSession) -> str:
    return f"{settings.APP_BASE_URL.rstrip('/')}/take/{session.id}?token={session.access_token}"


def _send_invite_email(session: InterviewSession) -> None:
    if not session.candidate_email:
        return
    role_label = ROLE_LABELS.get(session.role, session.role)
    link = _invite_url(session)
    body = (
        f"Hi {session.candidate_name},\n\n"
        f"You've been invited to complete a {role_label} technical screening.\n\n"
        f"Start your interview here: {link}\n\n"
        "The interview is self-paced — take your time on each question.\n"
    )
    send_text_email(to_email=session.candidate_email, subject="Your technical interview invite", body=body)


def require_owned_session(
    session_id: str,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InterviewSession:
    """
    Every session-scoped endpoint depends on this instead of querying InterviewSession
    directly, so knowing a session_id is never enough on its own — the caller must also
    be logged in as the user who created it. 404 (not 403) either way, so a wrong owner
    can't distinguish "not yours" from "doesn't exist."
    """
    session = db.query(InterviewSession).filter_by(id=session_id).first()
    if not session or session.user_id != current_user.id:
        raise HTTPException(404, f"Session {session_id} not found")
    return session


def _looks_like_pdf(file_bytes: bytes) -> bool:
    return file_bytes.startswith(PDF_MAGIC)


@router.get("", response_model=dict)
@limiter.limit("60/minute")
def list_sessions(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List interview sessions created by the current user, paginated (default page size 20)."""
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    return orchestrator.list_sessions_for_user(db, current_user.id, limit=limit, offset=offset)


@router.post("", response_model=dict)
@limiter.limit("5/minute")
async def create_session(
    request: Request,
    candidate_name: str = Form(...),
    role: str = Form(...),
    candidate_email: Optional[str] = Form(None),
    resume: UploadFile = File(...),
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload resume PDF and create an interview session owned by the current user."""
    candidate_name = candidate_name.strip()
    if not candidate_name or len(candidate_name) > MAX_NAME_LENGTH:
        raise HTTPException(400, f"Candidate name must be 1-{MAX_NAME_LENGTH} characters.")

    if role not in ALLOWED_ROLES:
        raise HTTPException(400, f"Invalid role. Choose from: {', '.join(ALLOWED_ROLES)}")

    if candidate_email and not EMAIL_RE.match(candidate_email.strip()):
        raise HTTPException(400, "Invalid email address.")

    if not resume.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF resumes are supported.")

    pdf_bytes = await resume.read()
    if not pdf_bytes:
        raise HTTPException(400, "Uploaded resume is empty.")
    if len(pdf_bytes) > 5 * 1024 * 1024:
        raise HTTPException(400, "Resume file too large (max 5MB).")
    if not _looks_like_pdf(pdf_bytes):
        raise HTTPException(400, "Invalid PDF file format. Please upload a valid PDF.")

    try:
        # This is an `async def` endpoint, but orchestrator.create_session is a blocking
        # call (PDF parsing, embeddings, a synchronous Anthropic API request) with no
        # `await` of its own — called directly, it would freeze the whole event loop for
        # its duration, stalling every other concurrent request on this worker, not just
        # this one. run_in_threadpool offloads it the same way FastAPI auto-threadpools
        # plain `def` endpoints.
        session = await run_in_threadpool(
            orchestrator.create_session,
            db=db,
            user_id=current_user.id,
            candidate_name=candidate_name,
            role=role,
            resume_bytes=pdf_bytes,
            candidate_email=(candidate_email or "").strip(),
        )
    except Exception:
        logger.exception("Failed to create session for candidate %s", candidate_name)
        raise HTTPException(500, "Failed to create session. Please try again.")

    parsed = json.loads(session.resume_parsed or "{}")

    return {
        "session_id": session.id,
        "status": session.status.value,
        "parsed_resume": parsed,
        "invite_url": _invite_url(session),
        "message": "Session created. Send the candidate their invite link, or start the interview yourself.",
    }


@router.post("/{session_id}/start", response_model=dict)
@limiter.limit("10/minute")
def start_session(
    request: Request,
    session_id: str,
    db: DBSession = Depends(get_db),
    _session: InterviewSession = Depends(require_owned_session),
):
    """Start the interview — transitions to active and returns the first question."""
    try:
        session, question = orchestrator.start_session(db, session_id)
    except ValueError as e:
        # require_owned_session already confirmed the session exists, so a
        # ValueError here means it was already started, not "not found."
        raise HTTPException(409, str(e))
    except Exception:
        logger.exception("Failed to start session %s", session_id)
        raise HTTPException(500, "Failed to start session. Please try again.")

    return {
        "session_id": session.id,
        "status": session.status.value,
        "question": _format_question(question),
        "questions_remaining": settings.MAX_QUESTIONS - 1,
    }


@router.post("/{session_id}/answers", response_model=dict)
@limiter.limit("20/minute")
def submit_answer(
    request: Request,
    session_id: str,
    question_id: str,
    payload: AnswerSubmit,
    db: DBSession = Depends(get_db),
    _session: InterviewSession = Depends(require_owned_session),
):
    """Submit an answer to a question. Triggers evaluation and generates the next question."""
    answer_text = payload.answer_text.strip()
    if not answer_text:
        raise HTTPException(400, "Answer cannot be empty.")
    if len(answer_text) > 5000:
        raise HTTPException(400, "Answer is too long (max 5000 characters).")

    try:
        answer, next_q, is_complete = orchestrator.submit_answer_and_advance(db, session_id, question_id, answer_text)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception:
        logger.exception("Failed to submit answer for session %s", session_id)
        raise HTTPException(500, "Failed to submit answer. Please try again.")

    rationale = {}
    try:
        rationale = json.loads(answer.score_rationale or "{}")
    except Exception:
        pass

    session = db.query(InterviewSession).filter_by(id=session_id).first()

    return {
        "answer_id": answer.id,
        "score": answer.score,
        "rationale": rationale.get("rationale", ""),
        "strengths": rationale.get("strengths", ""),
        "gaps": rationale.get("gaps", ""),
        "next_question": _format_question(next_q) if next_q else None,
        "is_complete": is_complete,
        "questions_remaining": max(0, settings.MAX_QUESTIONS - session.current_question_index),
    }


@router.post("/{session_id}/complete", response_model=dict)
@limiter.limit("10/minute")
def complete_session(
    request: Request,
    session_id: str,
    db: DBSession = Depends(get_db),
    _session: InterviewSession = Depends(require_owned_session),
):
    """Finalize the interview and generate the report."""
    try:
        report = orchestrator.complete_session(db, session_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception:
        logger.exception("Failed to complete session %s", session_id)
        raise HTTPException(500, "Failed to generate report. Please try again.")

    return {
        "session_id": session_id,
        "report": {
            "summary": report.summary,
            "overall_score": report.overall_score,
            "topic_coverage": json.loads(report.topic_coverage or "{}"),
            "strengths": report.strengths,
            "gaps": report.gaps,
            "recommendation": report.recommendation,
        },
    }


@router.get("/{session_id}", response_model=dict)
@limiter.limit("60/minute")
def get_session(
    request: Request,
    session_id: str,
    db: DBSession = Depends(get_db),
    session: InterviewSession = Depends(require_owned_session),
):
    """Get full session state including all Q&A and report."""
    try:
        summary = orchestrator.get_session_summary(db, session_id)
    except ValueError as e:
        raise HTTPException(404, str(e))

    summary["invite_url"] = _invite_url(session)
    return summary


@router.post("/{session_id}/invite/send", response_model=dict)
@limiter.limit("5/minute")
def send_invite(
    request: Request,
    session_id: str,
    session: InterviewSession = Depends(require_owned_session),
):
    """(Re)send the candidate their invite email. Requires a candidate_email on the session."""
    if not session.candidate_email:
        raise HTTPException(400, "This session has no candidate email on file.")
    if session.status != SessionStatus.created:
        raise HTTPException(409, "This interview has already been started.")

    _send_invite_email(session)
    return {"message": f"Invite sent to {session.candidate_email}.", "invite_url": _invite_url(session)}


@router.get("/{session_id}/report", response_model=dict)
@limiter.limit("60/minute")
def get_report(
    request: Request,
    session_id: str,
    db: DBSession = Depends(get_db),
    _session: InterviewSession = Depends(require_owned_session),
):
    """Get the session report (must have called /complete first)."""
    try:
        summary = orchestrator.get_session_summary(db, session_id)
    except ValueError as e:
        raise HTTPException(404, str(e))

    if not summary.get("report"):
        raise HTTPException(400, "Report not yet generated. Call /complete first.")
    return summary["report"]


def _format_question(question) -> Optional[dict]:
    if question is None:
        return None
    return {
        "id": question.id,
        "text": question.text,
        "topic": question.topic,
        "difficulty": question.difficulty,
        "order": question.order,
        "source_context": question.source_context,
        "answer": None,
    }
