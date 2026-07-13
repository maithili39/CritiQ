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

from fastapi import APIRouter, Depends, HTTPException, Request
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
        "questions_answered": sum(1 for q in session.questions if q.answer is not None),
        "max_questions": settings.MAX_QUESTIONS,
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
    db: DBSession = Depends(get_db),
    session: InterviewSession = Depends(get_session_by_access_token),
):
    """Submit an answer. Returns only the next question — no score is shown to the candidate."""
    answer_text = payload.answer_text.strip()
    if not answer_text:
        raise HTTPException(400, "Answer cannot be empty.")
    if len(answer_text) > 5000:
        raise HTTPException(400, "Answer is too long (max 5000 characters).")

    try:
        _answer, next_q, is_complete = orchestrator.submit_answer_and_advance(db, session_id, question_id, answer_text)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception:
        logger.exception("Failed to submit candidate answer for session %s", session_id)
        raise HTTPException(500, "Failed to submit your answer. Please try again.")

    return {
        "next_question": _format_question(next_q) if next_q else None,
        "is_complete": is_complete,
    }


@router.post("/{session_id}/complete", response_model=dict)
@limiter.limit("10/minute")
def complete_candidate_session(
    request: Request,
    session_id: str,
    db: DBSession = Depends(get_db),
    session: InterviewSession = Depends(get_session_by_access_token),
):
    """Finalize the interview. The report is generated for the recruiter; the
    candidate only sees a confirmation, never the score or recommendation."""
    try:
        orchestrator.complete_session(db, session_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception:
        logger.exception("Failed to complete candidate session %s", session_id)
        raise HTTPException(500, "Failed to submit your interview. Please try again.")

    return {"message": "Thanks — your responses have been submitted for review."}
