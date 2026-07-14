"""Unit tests for interview_orchestrator, calling it directly (no HTTP layer)."""

import pytest
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.models.user import User
from app.services import interview_orchestrator as orchestrator


@pytest.fixture()
def db_session(db_engine):
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    db = session_local()
    yield db
    db.close()


@pytest.fixture()
def user(db_session):
    u = User(email="orchestrator-test@example.com", password_hash=hash_password("irrelevant1"))
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def test_create_session_stores_parsed_resume(db_session, user, mock_ai):
    session = orchestrator.create_session(
        db=db_session,
        user_id=user.id,
        candidate_name="Ada Lovelace",
        role="ai_ml",
        resume_bytes=b"%PDF-1.4 mock",
    )
    assert session.user_id == user.id
    assert session.status.value == "created"
    assert "PyTorch" in session.resume_parsed


def test_start_session_generates_first_question(db_session, user, mock_ai):
    session = orchestrator.create_session(
        db=db_session, user_id=user.id, candidate_name="Ada", role="ai_ml", resume_bytes=b"%PDF-1.4"
    )
    updated, question = orchestrator.start_session(db_session, session.id)
    assert updated.status.value == "active"
    assert question.order == 1


def test_get_next_question_returns_none_past_max(db_session, user, mock_ai, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_QUESTIONS", 1)
    session = orchestrator.create_session(
        db=db_session, user_id=user.id, candidate_name="Ada", role="ai_ml", resume_bytes=b"%PDF-1.4"
    )
    orchestrator.start_session(db_session, session.id)
    next_q = orchestrator.get_next_question(db_session, session.id, "an answer")
    assert next_q is None


def test_submit_answer_unknown_question_raises(db_session, user, mock_ai):
    session = orchestrator.create_session(
        db=db_session, user_id=user.id, candidate_name="Ada", role="ai_ml", resume_bytes=b"%PDF-1.4"
    )
    with pytest.raises(ValueError):
        orchestrator.submit_answer(db_session, session.id, "does-not-exist", "an answer")


def test_get_session_summary_missing_session_raises(db_session):
    with pytest.raises(ValueError):
        orchestrator.get_session_summary(db_session, "does-not-exist")


def test_complete_session_produces_report(db_session, user, mock_ai):
    session = orchestrator.create_session(
        db=db_session, user_id=user.id, candidate_name="Ada", role="ai_ml", resume_bytes=b"%PDF-1.4"
    )
    orchestrator.start_session(db_session, session.id)
    report = orchestrator.complete_session(db_session, session.id)
    assert report.recommendation == "yes"
    assert report.overall_score == 8.0


def test_submit_answer_and_advance_scores_and_generates_next_question(db_session, user, mock_ai):
    session = orchestrator.create_session(
        db=db_session, user_id=user.id, candidate_name="Ada", role="ai_ml", resume_bytes=b"%PDF-1.4"
    )
    _, first_question = orchestrator.start_session(db_session, session.id)

    answer, next_question, is_complete = orchestrator.submit_answer_and_advance(
        db_session, session.id, first_question.id, "A thorough answer."
    )

    assert answer.score == 8.0
    assert next_question is not None
    assert next_question.order == first_question.order + 1
    assert is_complete is False


def test_submit_answer_and_advance_completes_on_last_question(db_session, user, mock_ai, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_QUESTIONS", 1)
    session = orchestrator.create_session(
        db=db_session, user_id=user.id, candidate_name="Ada", role="ai_ml", resume_bytes=b"%PDF-1.4"
    )
    _, first_question = orchestrator.start_session(db_session, session.id)

    answer, next_question, is_complete = orchestrator.submit_answer_and_advance(
        db_session, session.id, first_question.id, "A thorough answer."
    )

    assert answer.score == 8.0
    assert next_question is None
    assert is_complete is True


def test_submit_answer_and_advance_still_scores_if_next_question_generation_fails(
    db_session, user, mock_ai, monkeypatch
):
    """A next-question generation failure must not cost the candidate their score for
    the answer they already submitted — the two Claude calls are independent."""
    session = orchestrator.create_session(
        db=db_session, user_id=user.id, candidate_name="Ada", role="ai_ml", resume_bytes=b"%PDF-1.4"
    )
    # Question #1 must still generate normally via start_session before we break it.
    _, first_question = orchestrator.start_session(db_session, session.id)

    def failing_generate_question(**kwargs):
        raise RuntimeError("simulated model failure")

    monkeypatch.setattr(mock_ai, "generate_question", failing_generate_question)

    answer, next_question, is_complete = orchestrator.submit_answer_and_advance(
        db_session, session.id, first_question.id, "A thorough answer."
    )

    assert answer.score == 8.0
    assert next_question is None
    assert is_complete is True
