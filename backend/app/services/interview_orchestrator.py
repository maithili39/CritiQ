"""
Interview Orchestrator

Ties together: resume parsing → RAG retrieval → question generation → answer evaluation.
Acts as the single source of truth for interview session state transitions.
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session as DBSession, load_only, selectinload

from app.models.session import InterviewSession, Question, Answer, Report, SessionStatus
from app.services.resume_parser import parse_resume, extract_text_from_pdf_bytes
from app.services.question_generator import generate_question, evaluate_answer, generate_report
from app.core.config import settings

logger = logging.getLogger(__name__)


def create_session(
    db: DBSession,
    user_id: str,
    candidate_name: str,
    role: str,
    resume_bytes: bytes,
    candidate_email: str = "",
) -> InterviewSession:
    """
    Creates a new interview session:
    1. Extracts text from PDF
    2. Parses resume with Claude
    3. Persists session to DB
    """
    resume_text = extract_text_from_pdf_bytes(resume_bytes)
    parsed = parse_resume(resume_text)

    session = InterviewSession(
        user_id=user_id,
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        role=role,
        resume_text=resume_text,
        resume_parsed=json.dumps(parsed),
        status=SessionStatus.created,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_sessions_for_user(db: DBSession, user_id: str, limit: int = 20, offset: int = 0) -> Dict:
    """
    Paginated, lightweight session list for the 'my sessions' view — no Q&A payload.

    Uses selectinload for `report` (one extra query total, not one per row — the
    naive `s.report` access below used to lazy-load per session, an N+1 that's
    invisible at 10 sessions and real at 10,000) and load_only to skip fetching
    `resume_text`/`resume_parsed`, which aren't needed for the list view and can be
    several KB each.
    """
    base_query = db.query(InterviewSession).filter_by(user_id=user_id)
    total = base_query.count()

    sessions = (
        base_query
        .options(
            load_only(
                InterviewSession.id,
                InterviewSession.candidate_name,
                InterviewSession.role,
                InterviewSession.status,
                InterviewSession.created_at,
                InterviewSession.completed_at,
            ),
            selectinload(InterviewSession.report),
        )
        .order_by(InterviewSession.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return {
        "sessions": [
            {
                "id": s.id,
                "candidate_name": s.candidate_name,
                "role": s.role,
                "status": s.status.value,
                "overall_score": s.report.overall_score if s.report else None,
                "created_at": s.created_at.isoformat(),
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in sessions
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def start_session(db: DBSession, session_id: str) -> Tuple[InterviewSession, Question]:
    """
    Transitions session to active and generates the first question.
    """
    session = _get_session(db, session_id)
    if session.status != SessionStatus.created:
        raise ValueError(f"Session {session_id} has already been started.")

    parsed_resume = json.loads(session.resume_parsed or "{}")

    session.status = SessionStatus.active
    db.commit()

    question = _generate_and_store_question(db, session, parsed_resume, question_number=1)
    return session, question


def get_next_question(
    db: DBSession,
    session_id: str,
    previous_answer_text: Optional[str] = None,
) -> Optional[Question]:
    """
    Generates and returns the next question.
    Returns None if max questions reached.
    """
    session = _get_session(db, session_id)

    if session.current_question_index >= settings.MAX_QUESTIONS:
        return None

    parsed_resume = json.loads(session.resume_parsed or "{}")
    previous_questions = [q.text for q in session.questions]

    question = _generate_and_store_question(
        db,
        session,
        parsed_resume,
        question_number=session.current_question_index + 1,
        previous_questions=previous_questions,
        previous_answer=previous_answer_text,
    )
    return question


def submit_answer(
    db: DBSession,
    session_id: str,
    question_id: str,
    answer_text: str,
) -> Answer:
    """
    Stores a candidate answer and evaluates it with Claude.
    """
    session = _get_session(db, session_id)
    question = db.query(Question).filter_by(id=question_id, session_id=session_id).first()
    if not question:
        raise ValueError(f"Question {question_id} not found in session {session_id}")

    # Evaluate answer
    evaluation = evaluate_answer(
        question=question.text,
        answer=answer_text,
        context=question.source_context or "",
        experience_level=json.loads(session.resume_parsed or "{}").get("experience_level", "mid"),
    )

    answer = Answer(
        question_id=question_id,
        text=answer_text,
        score=evaluation.get("score"),
        score_rationale=json.dumps({
            "rationale": evaluation.get("rationale", ""),
            "strengths": evaluation.get("strengths", ""),
            "gaps": evaluation.get("gaps", ""),
        }),
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)
    return answer


def submit_answer_and_advance(
    db: DBSession,
    session_id: str,
    question_id: str,
    answer_text: str,
) -> Tuple[Answer, Optional[Question], bool]:
    """
    Scores the submitted answer and generates the next question concurrently,
    instead of the two sequential Claude calls `submit_answer` then
    `get_next_question` used to require. They're independent — question
    generation only needs the raw answer text, not its score — so running them
    in parallel roughly halves the latency a candidate waits between one
    question and the next, without needing a background job queue.
    """
    session = _get_session(db, session_id)
    question = db.query(Question).filter_by(id=question_id, session_id=session_id).first()
    if not question:
        raise ValueError(f"Question {question_id} not found in session {session_id}")

    parsed_resume = json.loads(session.resume_parsed or "{}")
    experience_level = parsed_resume.get("experience_level", "mid")
    is_last = session.current_question_index >= settings.MAX_QUESTIONS
    previous_questions = [q.text for q in session.questions]
    next_question_number = session.current_question_index + 1

    with ThreadPoolExecutor(max_workers=2) as pool:
        eval_future = pool.submit(
            evaluate_answer,
            question=question.text,
            answer=answer_text,
            context=question.source_context or "",
            experience_level=experience_level,
        )
        question_future = None
        if not is_last:
            question_future = pool.submit(
                generate_question,
                role=session.role,
                parsed_resume=parsed_resume,
                previous_questions=previous_questions,
                previous_answer=answer_text,
                question_number=next_question_number,
            )

        # No fake score on failure — let a scoring error propagate to the caller
        # rather than silently grading the candidate off a system error.
        evaluation = eval_future.result()

        generated = None
        if question_future is not None:
            try:
                generated = question_future.result()
            except Exception:
                logger.exception("Failed to generate next question for session %s", session_id)

    answer = Answer(
        question_id=question_id,
        text=answer_text,
        score=evaluation.get("score"),
        score_rationale=json.dumps({
            "rationale": evaluation.get("rationale", ""),
            "strengths": evaluation.get("strengths", ""),
            "gaps": evaluation.get("gaps", ""),
        }),
    )
    db.add(answer)

    next_question = None
    if generated is not None:
        next_question = Question(
            session_id=session.id,
            text=generated["text"],
            topic=generated.get("topic", ""),
            difficulty=generated.get("difficulty", "mid"),
            source_context=generated.get("source_context", ""),
            order=next_question_number,
        )
        db.add(next_question)
        session.current_question_index = next_question_number

    db.commit()
    db.refresh(answer)
    if next_question:
        db.refresh(next_question)

    is_complete = is_last or next_question is None
    return answer, next_question, is_complete


def complete_session(db: DBSession, session_id: str) -> Report:
    """
    Marks session complete and generates the final report.
    """
    session = _get_session(db, session_id)
    parsed_resume = json.loads(session.resume_parsed or "{}")

    # Build QA pairs for report generation
    qa_pairs = []
    for q in sorted(session.questions, key=lambda x: x.order):
        pair = {
            "question": q.text,
            "topic": q.topic,
            "answer": q.answer.text if q.answer else "",
            "score": q.answer.score if q.answer else None,
        }
        qa_pairs.append(pair)

    report_data = generate_report({
        "qa_pairs": qa_pairs,
        "candidate": {
            "name": session.candidate_name,
            "experience_level": parsed_resume.get("experience_level", "mid"),
        },
        "role": session.role,
    })

    # Persist report
    report = Report(
        session_id=session_id,
        summary=report_data.get("summary", ""),
        overall_score=report_data.get("overall_score"),
        topic_coverage=json.dumps(report_data.get("topic_coverage", {})),
        strengths=report_data.get("strengths", ""),
        gaps=report_data.get("gaps", ""),
        recommendation=report_data.get("recommendation", "maybe"),
    )
    db.add(report)

    session.status = SessionStatus.completed
    session.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return report


def get_session_summary(db: DBSession, session_id: str) -> Dict:
    """Returns full session state including all Q&A and report."""
    session = _get_session(db, session_id)
    parsed = json.loads(session.resume_parsed or "{}")

    questions_data = []
    for q in sorted(session.questions, key=lambda x: x.order):
        q_data = {
            "id": q.id,
            "text": q.text,
            "topic": q.topic,
            "difficulty": q.difficulty,
            "order": q.order,
            "source_context": q.source_context,
            "answer": None,
        }
        if q.answer:
            rationale = {}
            try:
                rationale = json.loads(q.answer.score_rationale or "{}")
            except Exception:
                pass
            q_data["answer"] = {
                "id": q.answer.id,
                "text": q.answer.text,
                "score": q.answer.score,
                "rationale": rationale.get("rationale", ""),
                "strengths": rationale.get("strengths", ""),
                "gaps": rationale.get("gaps", ""),
            }
        questions_data.append(q_data)

    report_data = None
    if session.report:
        r = session.report
        report_data = {
            "summary": r.summary,
            "overall_score": r.overall_score,
            "topic_coverage": json.loads(r.topic_coverage or "{}"),
            "strengths": r.strengths,
            "gaps": r.gaps,
            "recommendation": r.recommendation,
        }

    return {
        "id": session.id,
        "candidate_name": session.candidate_name,
        "candidate_email": session.candidate_email,
        "role": session.role,
        "status": session.status.value,
        "current_question_index": session.current_question_index,
        "max_questions": settings.MAX_QUESTIONS,
        "parsed_resume": parsed,
        "questions": questions_data,
        "report": report_data,
        "created_at": session.created_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }


# --- Internal helpers ---

def _get_session(db: DBSession, session_id: str) -> InterviewSession:
    session = db.query(InterviewSession).filter_by(id=session_id).first()
    if not session:
        raise ValueError(f"Session {session_id} not found")
    return session


def _generate_and_store_question(
    db: DBSession,
    session: InterviewSession,
    parsed_resume: Dict,
    question_number: int,
    previous_questions: list = None,
    previous_answer: str = None,
) -> Question:
    previous_questions = previous_questions or []

    generated = generate_question(
        role=session.role,
        parsed_resume=parsed_resume,
        previous_questions=previous_questions,
        previous_answer=previous_answer,
        question_number=question_number,
    )

    question = Question(
        session_id=session.id,
        text=generated["text"],
        topic=generated.get("topic", ""),
        difficulty=generated.get("difficulty", "mid"),
        source_context=generated.get("source_context", ""),
        order=question_number,
    )
    db.add(question)
    session.current_question_index = question_number
    db.commit()
    db.refresh(question)
    return question
