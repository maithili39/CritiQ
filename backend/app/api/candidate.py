"""
Candidate-facing session API.

Authenticated by the per-session invite token (?token=...) instead of a user
JWT — a candidate never needs an account to take an interview. Responses are
deliberately reduced compared to the recruiter-side /sessions endpoints:
no per-answer score/rationale, no source_context, no final report. Those are
scoring/traceability tools for the recruiter's judgment, not something a
candidate should see live (it would let them game later answers) or at all
(the recommendation is an internal hiring decision).
"""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.api.deps import get_session_by_access_token
from app.models.session import InterviewSession, SessionStatus
from app.schemas.interview import AnswerSubmit
from app.services import interview_orchestrator as orchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/candidate/sessions", tags=["candidate"])


def _format_question(question) -> Optional[dict]:
    if question is None:
        return None
    return {
        "id": question.id,
        "text": question.text,
        "topic": question.topic,
        "difficulty": question.difficulty,
        "order": question.order,
    }


@router.get("/{session_id}", response_model=dict)
@limiter.limit("60/minute")
def get_candidate_session(
    request: Request,
    session_id: str,
    session: InterviewSession = Depends(get_session_by_access_token),
):
    """Candidate-safe view: invite status and the current question, nothing scored."""
    current_question = max(session.questions, key=lambda q: q.order, default=None) \
        if session.status != SessionStatus.created else None

    return {
        "session_id": session.id,
        "candidate_name": session.candidate_name,
        "role": session.role,
        "status": session.status.value,
        "question": _format_question(current_question),
        "questions_answered": sum(1 for q in session.questions if q.answer and q.answer.score is not None),
        "max_questions": settings.MAX_QUESTIONS,
        "is_processing": session.is_processing,
        "processing_error": session.processing_error,
    }


@router.post("/{session_id}/start", response_model=dict)
@limiter.limit("10/minute")
def start_candidate_session(
    request: Request,
    session_id: str,
    db: DBSession = Depends(get_db),
    session: InterviewSession = Depends(get_session_by_access_token),
):
    """Candidate begins their interview. Can only be called once per session."""
    try:
        _, question = orchestrator.start_session(db, session_id)
    except ValueError as e:
        raise HTTPException(409, str(e))
    except Exception:
        logger.exception("Failed to start candidate session %s", session_id)
        raise HTTPException(500, "Failed to start the interview. Please try again.")

    return {"session_id": session_id, "status": "active", "question": _format_question(question)}


@router.post("/{session_id}/answers", response_model=dict)
@limiter.limit("20/minute")
def submit_candidate_answer(
    request: Request,
    session_id: str,
    question_id: str,
    payload: AnswerSubmit,
    background_tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
    session: InterviewSession = Depends(get_session_by_access_token),
):
    """
    Submit an answer. Returns immediately (202) instead of waiting on scoring +
    next-question generation — those run in a background task, and the frontend
    polls GET /{session_id} for is_processing to clear. This is what keeps a
    candidate from sitting on the Claude round-trip for every single answer.
    """
    answer_text = payload.answer_text.strip()
    if not answer_text:
        raise HTTPException(400, "Answer cannot be empty.")
    if len(answer_text) > 5000:
        raise HTTPException(400, "Answer is too long (max 5000 characters).")

    try:
        orchestrator.submit_answer_pending(db, session_id, question_id, answer_text)
    except ValueError as e:
        raise HTTPException(409 if "already processing" in str(e) else 404, str(e))
    except Exception:
        logger.exception("Failed to submit candidate answer for session %s", session_id)
        raise HTTPException(500, "Failed to submit your answer. Please try again.")

    background_tasks.add_task(
        orchestrator.process_answer_in_background, session_id, question_id, answer_text
    )
    return {"status": "processing"}


@router.post("/{session_id}/complete", response_model=dict)
@limiter.limit("10/minute")
def complete_candidate_session(
    request: Request,
    session_id: str,
    db: DBSession = Depends(get_db),
    session: InterviewSession = Depends(get_session_by_access_token),
):
    """
    Finalize the interview. In the normal flow, the background task from the last
    answer already auto-completes the session (see process_answer_in_background),
    so this is a fallback/no-op in that case rather than a required step.

    Guard against duplicate report rows: check both the session status *and*
    whether a report already exists. The background task may have already written
    the report while the status transition was still in-flight, so relying on
    status alone is not sufficient.
    """
    if session.status == SessionStatus.completed or session.report:
        return {"message": "Thanks — your responses have been submitted for review."}

    try:
        orchestrator.complete_session(db, session_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception:
        logger.exception("Failed to complete candidate session %s", session_id)
        raise HTTPException(500, "Failed to submit your interview. Please try again.")

    return {"message": "Thanks — your responses have been submitted for review."}
