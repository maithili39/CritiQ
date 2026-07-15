"""
Interview Orchestrator

Ties together: resume parsing → RAG retrieval → question generation → answer evaluation.
Acts as the single source of truth for interview session state transitions.
"""

import contextlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import load_only, selectinload

from app.core.config import settings
from app.models.session import Answer, InterviewSession, Question, Report, SessionStatus
from app.services.integrity import compute_session_integrity
from app.services.question_generator import evaluate_answer_with_consistency, generate_question, generate_report
from app.services.resume_parser import extract_text_from_pdf_bytes, parse_resume
from app.services.role_profiles import get_role_profile

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


def list_sessions_for_user(db: DBSession, user_id: str, limit: int = 20, offset: int = 0) -> dict:
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
        base_query.options(
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


def start_session(db: DBSession, session_id: str) -> tuple[InterviewSession, Question]:
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
    previous_answer_text: str | None = None,
) -> Question | None:
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

    # Evaluate answer against the role's rubric, with a second-pass consistency check
    evaluation = evaluate_answer_with_consistency(
        question=question.text,
        answer=answer_text,
        context=question.source_context or "",
        experience_level=json.loads(session.resume_parsed or "{}").get("experience_level", "mid"),
        role=session.role,
    )

    answer = Answer(
        question_id=question_id,
        text=answer_text,
        score=evaluation.get("score"),
        needs_human_review=evaluation.get("needs_human_review", False),
        score_rationale=json.dumps(_evaluation_to_rationale_blob(evaluation)),
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
) -> tuple[Answer, Question | None, bool]:
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
            evaluate_answer_with_consistency,
            question=question.text,
            answer=answer_text,
            context=question.source_context or "",
            experience_level=experience_level,
            role=session.role,
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
                role_profile=get_role_profile(db, session.role, experience_level),
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
        needs_human_review=evaluation.get("needs_human_review", False),
        score_rationale=json.dumps(_evaluation_to_rationale_blob(evaluation)),
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

    Idempotent: if a Report row already exists for this session it is returned
    immediately without generating a second one. This prevents duplicate Report
    rows when the endpoint is called more than once (e.g. double-click, retry,
    or the recruiter calling /complete after the candidate background-task path
    already auto-completed the session).
    """
    session = _get_session(db, session_id)
    if session.report:
        # Already completed — return the existing report without touching the DB.
        return session.report
    report = _build_and_store_report(db, session)
    db.commit()
    db.refresh(report)
    return report


def submit_answer_pending(
    db: DBSession,
    session_id: str,
    question_id: str,
    answer_text: str,
    integrity_data: dict | None = None,
) -> Answer:
    """
    Candidate-flow entry point: stores the answer text immediately (score not yet
    known) and marks the session as processing. The actual scoring + next-question
    (or report) generation happens in `process_answer_in_background`, scheduled by
    the caller via FastAPI's BackgroundTasks — the HTTP response returns right
    after this, instead of the candidate waiting on the Claude round-trip.

    integrity_data: optional dict with response_time_ms, paste_detected,
    tab_switch_count, camera_snapshot from the frontend anti-cheating suite.
    """
    session = _get_session(db, session_id)
    question = db.query(Question).filter_by(id=question_id, session_id=session_id).first()
    if not question:
        raise ValueError(f"Question {question_id} not found in session {session_id}")
    if session.is_processing:
        raise ValueError(f"Session {session_id} is already processing an answer.")

    integrity_data = integrity_data or {}
    answer = Answer(
        question_id=question_id,
        text=answer_text,
        response_time_ms=integrity_data.get("response_time_ms"),
        paste_detected=integrity_data.get("paste_detected", False),
        tab_switch_count=integrity_data.get("tab_switch_count", 0),
        camera_snapshot=integrity_data.get("camera_snapshot"),
    )
    db.add(answer)
    session.is_processing = True
    session.processing_error = None
    db.commit()
    db.refresh(answer)
    return answer


def process_answer_in_background(session_id: str, question_id: str, answer_text: str) -> None:
    """
    Runs off the request/response cycle (see submit_answer_pending above). Opens
    its own DB session since the request-scoped one from `get_db` is already
    closed by the time a background task runs.
    """
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        session = _get_session(db, session_id)
        question = db.query(Question).filter_by(id=question_id, session_id=session_id).first()
        # Filter on score IS NULL to unambiguously target the pending answer created
        # by submit_answer_pending. Filtering by question_id alone could pick up a
        # stale scored answer if the question were somehow re-answered (race/bug).
        answer = db.query(Answer).filter_by(question_id=question_id).filter(Answer.score.is_(None)).first()
        if not question or not answer:
            return

        parsed_resume = json.loads(session.resume_parsed or "{}")
        experience_level = parsed_resume.get("experience_level", "mid")
        is_last = session.current_question_index >= settings.MAX_QUESTIONS
        previous_questions = [q.text for q in session.questions]
        next_question_number = session.current_question_index + 1

        with ThreadPoolExecutor(max_workers=2) as pool:
            eval_future = pool.submit(
                evaluate_answer_with_consistency,
                question=question.text,
                answer=answer_text,
                context=question.source_context or "",
                experience_level=experience_level,
                role=session.role,
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
                    role_profile=get_role_profile(db, session.role, experience_level),
                )

            evaluation = eval_future.result()

            generated = None
            if question_future is not None:
                try:
                    generated = question_future.result()
                except Exception:
                    logger.exception("Failed to generate next question for session %s", session_id)

        answer.score = evaluation.get("score")
        answer.needs_human_review = evaluation.get("needs_human_review", False)
        answer.score_rationale = json.dumps(_evaluation_to_rationale_blob(evaluation))

        # Build integrity_flags based on collected telemetry signals.
        # This runs after scoring so we can potentially correlate suspiciously
        # polished answers with very short response times in future.
        reasons: list[str] = []
        if answer.paste_detected:
            reasons.append("paste_detected")
        if answer.tab_switch_count and answer.tab_switch_count > 0:
            reasons.append(f"tab_switched_{answer.tab_switch_count}x")
        if answer.response_time_ms is not None and answer.response_time_ms < 15_000:
            reasons.append("sub_15s_response")
        # Suspiciously polished (high score) + very fast = flag for review
        score = evaluation.get("score") or 0
        if score >= 8 and answer.response_time_ms is not None and answer.response_time_ms < 30_000:
            reasons.append("high_score_fast_response")
        # Two independent rubric passes disagreed enough to distrust either alone
        if answer.needs_human_review:
            reasons.append(f"score_variance_{evaluation.get('score_variance')}")

        answer.integrity_flags = json.dumps(
            {
                "suspicious": len(reasons) > 0,
                "reasons": reasons,
            }
        )

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
            session.is_processing = False
            db.commit()
        else:
            # Last question (or generation failed on the last one) - auto-complete
            # the interview and generate the report, so the candidate doesn't need
            # a separate "complete" call in the async flow.
            _build_and_store_report(db, session)
            session.is_processing = False
            db.commit()
    except Exception as exc:
        logger.exception("Background answer processing failed for session %s", session_id)
        try:
            session = db.query(InterviewSession).filter_by(id=session_id).first()
            if session:
                session.is_processing = False
                session.processing_error = str(exc)
                db.commit()
        except Exception:
            logger.exception("Failed to record processing_error for session %s", session_id)
    finally:
        db.close()


def get_session_summary(db: DBSession, session_id: str) -> dict:
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
            with contextlib.suppress(Exception):
                rationale = json.loads(q.answer.score_rationale or "{}")
            integrity = {}
            with contextlib.suppress(Exception):
                integrity = json.loads(q.answer.integrity_flags or "{}")
            q_data["answer"] = {
                "id": q.answer.id,
                "text": q.answer.text,
                "score": q.answer.score,
                "rationale": rationale.get("rationale", ""),
                "strengths": rationale.get("strengths", ""),
                "gaps": rationale.get("gaps", ""),
                "dimension_scores": rationale.get("dimension_scores", {}),
                "rubric_version": rationale.get("rubric_version"),
                "score_variance": rationale.get("score_variance"),
                "needs_human_review": q.answer.needs_human_review,
                "submitted_at": q.answer.submitted_at.isoformat() if q.answer.submitted_at else None,
                "response_time_ms": q.answer.response_time_ms,
                "paste_detected": q.answer.paste_detected,
                "tab_switch_count": q.answer.tab_switch_count,
                "integrity_flags": integrity,
                "has_camera_snapshot": bool(q.answer.camera_snapshot),
            }
        questions_data.append(q_data)

    report_data = None
    if session.report:
        r = session.report
        integrity_summary = {}
        with contextlib.suppress(Exception):
            integrity_summary = json.loads(r.integrity_summary or "{}")
        report_data = {
            "summary": r.summary,
            "overall_score": r.overall_score,
            "topic_coverage": json.loads(r.topic_coverage or "{}"),
            "strengths": r.strengths,
            "gaps": r.gaps,
            "recommendation": r.recommendation,
            "integrity_summary": integrity_summary,
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
        "outcome": session.outcome,
        "outcome_note": session.outcome_note,
        "outcome_at": session.outcome_at.isoformat() if session.outcome_at else None,
        "created_at": session.created_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }


# --- Hiring-outcome feedback & score calibration ---

# Recruiter-recorded ground truth. Ordered worst→best so we can correlate against
# the AI's numeric overall_score.
VALID_OUTCOMES = ("rejected", "no_show", "hired", "hired_strong")
# Maps outcome → a 0-10 "actual" scale, so we can compare against the predicted
# overall_score. no_show is excluded from correlation (no signal about quality).
_OUTCOME_SCALE = {"rejected": 2.5, "hired": 7.5, "hired_strong": 9.5}


def set_session_outcome(db: DBSession, session_id: str, outcome: str, note: str = "") -> InterviewSession:
    """Records the real post-interview hiring outcome for a session (ground truth)."""
    if outcome not in VALID_OUTCOMES:
        raise ValueError(f"Outcome must be one of: {', '.join(VALID_OUTCOMES)}")
    session = _get_session(db, session_id)
    session.outcome = outcome
    session.outcome_note = (note or "").strip() or None
    session.outcome_at = datetime.now(UTC)
    db.commit()
    db.refresh(session)
    return session


def compute_calibration(db: DBSession, user_id: str) -> dict:
    """
    Correlates the AI's predicted overall_score against recruiter-recorded outcomes
    across all of this user's scored sessions — the feedback loop that turns
    "an LLM scored someone" into "a screener validated against real hires".

    Returns summary stats plus a Pearson correlation between predicted score and
    the mapped outcome scale (null until there are >= 3 comparable data points).
    """
    rows = (
        db.query(InterviewSession, Report)
        .join(Report, Report.session_id == InterviewSession.id)
        .filter(
            InterviewSession.user_id == user_id,
            InterviewSession.outcome.isnot(None),
            Report.overall_score.isnot(None),
        )
        .all()
    )

    labeled = [
        {
            "session_id": s.id,
            "candidate_name": s.candidate_name,
            "role": s.role,
            "predicted_score": r.overall_score,
            "recommendation": r.recommendation,
            "outcome": s.outcome,
        }
        for s, r in rows
    ]

    # Points usable for correlation (no_show carries no quality signal).
    points = [(d["predicted_score"], _OUTCOME_SCALE[d["outcome"]]) for d in labeled if d["outcome"] in _OUTCOME_SCALE]

    correlation = _pearson([p for p, _ in points], [a for _, a in points]) if len(points) >= 3 else None

    # Simple confusion-style buckets: did a "hire recommendation" (score >= 6.5)
    # actually result in a hire?
    hired_outcomes = {"hired", "hired_strong"}
    tp = sum(1 for d in labeled if d["predicted_score"] >= 6.5 and d["outcome"] in hired_outcomes)
    fp = sum(1 for d in labeled if d["predicted_score"] >= 6.5 and d["outcome"] == "rejected")
    fn = sum(1 for d in labeled if d["predicted_score"] < 6.5 and d["outcome"] in hired_outcomes)
    tn = sum(1 for d in labeled if d["predicted_score"] < 6.5 and d["outcome"] == "rejected")

    return {
        "total_labeled": len(labeled),
        "correlation": round(correlation, 3) if correlation is not None else None,
        "confusion": {"true_positive": tp, "false_positive": fp, "false_negative": fn, "true_negative": tn},
        "points": labeled,
    }


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n == 0:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return None
    return cov / (vx**0.5 * vy**0.5)


# --- Internal helpers ---


def _evaluation_to_rationale_blob(evaluation: dict) -> dict:
    """Packs the rubric-based evaluation into the JSON blob stored in
    Answer.score_rationale, so dimension scores and the consistency check are
    auditable later without another migration."""
    return {
        "rationale": evaluation.get("rationale", ""),
        "strengths": evaluation.get("strengths", ""),
        "gaps": evaluation.get("gaps", ""),
        "dimension_scores": evaluation.get("dimension_scores", {}),
        "rubric_version": evaluation.get("rubric_version"),
        "score_variance": evaluation.get("score_variance"),
        "consistency_check_score": evaluation.get("consistency_check_score"),
    }


def _get_session(db: DBSession, session_id: str) -> InterviewSession:
    session = db.query(InterviewSession).filter_by(id=session_id).first()
    if not session:
        raise ValueError(f"Session {session_id} not found")
    return session


def _build_and_store_report(db: DBSession, session: InterviewSession) -> Report:
    """Generates and persists the final report, and flips the session to completed.
    Does not commit - the caller commits (some callers still have other state to
    flush in the same transaction, e.g. is_processing in the background-task path)."""
    parsed_resume = json.loads(session.resume_parsed or "{}")

    qa_pairs = []
    integrity_inputs = []
    for q in sorted(session.questions, key=lambda x: x.order):
        qa_pairs.append(
            {
                "question": q.text,
                "topic": q.topic,
                "answer": q.answer.text if q.answer else "",
                "score": q.answer.score if q.answer else None,
            }
        )
        if q.answer:
            integrity_inputs.append(
                {
                    "score": q.answer.score,
                    "response_time_ms": q.answer.response_time_ms,
                    "paste_detected": q.answer.paste_detected,
                    "tab_switch_count": q.answer.tab_switch_count,
                }
            )

    # Fuse per-answer telemetry into one explainable session-level integrity score.
    integrity_summary = compute_session_integrity(integrity_inputs)

    report_data = generate_report(
        {
            "qa_pairs": qa_pairs,
            "candidate": {
                "name": session.candidate_name,
                "experience_level": parsed_resume.get("experience_level", "mid"),
            },
            "role": session.role,
        }
    )

    report = Report(
        session_id=session.id,
        summary=report_data.get("summary", ""),
        overall_score=report_data.get("overall_score"),
        topic_coverage=json.dumps(report_data.get("topic_coverage", {})),
        strengths=report_data.get("strengths", ""),
        gaps=report_data.get("gaps", ""),
        recommendation=report_data.get("recommendation", "maybe"),
        integrity_summary=json.dumps(integrity_summary),
    )
    db.add(report)

    session.status = SessionStatus.completed
    session.completed_at = datetime.now(UTC)
    return report


def _generate_and_store_question(
    db: DBSession,
    session: InterviewSession,
    parsed_resume: dict,
    question_number: int,
    previous_questions: list | None = None,
    previous_answer: str | None = None,
) -> Question:
    previous_questions = previous_questions or []
    experience_level = parsed_resume.get("experience_level", "mid")

    generated = generate_question(
        role=session.role,
        parsed_resume=parsed_resume,
        previous_questions=previous_questions,
        previous_answer=previous_answer,
        question_number=question_number,
        role_profile=get_role_profile(db, session.role, experience_level),
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
