"""
Shared pytest fixtures.

Tests run against an in-memory SQLite DB (fast, no external Postgres needed) rather
than the real Alembic-managed schema — the models are simple enough that SQLite is a
faithful stand-in for correctness testing. Every test that calls Claude goes through
mocked resume_parser/question_generator functions, so the suite runs with no network
access and no real ANTHROPIC_API_KEY.
"""

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("JWT_SECRET", "test-secret-for-pytest-only")
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.core.database as db_module
from app.core.database import Base, get_db
from app.core.limiter import limiter
from app.main import app
from app.models import session as _session_models
from app.models import user as _user_models

# CI also runs the whole suite against a real Postgres service container by
# setting TEST_DATABASE_URL, closing the SQLite-vs-Postgres behavior gap
# (JSON/datetime/constraint semantics) without slowing down local runs.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")


@pytest.fixture()
def db_engine():
    if TEST_DATABASE_URL:
        engine = create_engine(TEST_DATABASE_URL)
    else:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def client(db_engine):
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    limiter.enabled = False  # rate limits would make a fast test suite flaky/order-dependent

    # BackgroundTasks (e.g. process_answer_in_background) open their own DB session
    # directly via `app.core.database.SessionLocal` rather than through the get_db
    # dependency (they outlive the request, so they can't reuse the request-scoped
    # session) - patch the module-level SessionLocal too, or they'd hit the real
    # production engine instead of this test's isolated in-memory one.
    original_session_local = db_module.SessionLocal
    db_module.SessionLocal = testing_session_local

    with TestClient(app) as test_client:
        yield test_client

    db_module.SessionLocal = original_session_local
    app.dependency_overrides.clear()
    limiter.enabled = True


@pytest.fixture()
def registered_user(client):
    """Registers a user and returns (email, password, auth_headers)."""
    email, password = "candidate-owner@example.com", "correct-horse-battery"
    res = client.post("/api/auth/register", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"email": email, "password": password, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture()
def mock_ai(monkeypatch):
    """
    Stubs every Claude-backed call the orchestrator makes, so the test suite never hits
    the network or needs a real ANTHROPIC_API_KEY. Patched on interview_orchestrator's
    own namespace, since it imported these functions by name (`from ... import x`),
    which binds a separate reference that patching the origin module wouldn't affect.
    """
    import app.services.interview_orchestrator as orchestrator

    question_counter = {"n": 0}

    def fake_extract_text(_pdf_bytes: bytes) -> str:
        return "Jane Doe\nSenior ML Engineer\nSkills: PyTorch, NLP, MLOps"

    def fake_parse_resume(_resume_text: str) -> dict:
        return {
            "skills": ["PyTorch", "NLP"],
            "technologies": ["Python", "Docker"],
            "experience_level": "senior",
            "domains": ["machine learning"],
            "years_of_experience": 6,
            "education": "MSc Computer Science",
            "summary": "Senior ML engineer with NLP focus.",
        }

    def fake_generate_question(**kwargs) -> dict:
        question_counter["n"] += 1
        n = question_counter["n"]
        return {
            "text": f"Mock question #{n} about {kwargs.get('role')}",
            "topic": f"Topic {n}",
            "difficulty": "senior",
            "source_context": "mock retrieved context",
            "sources": [],
        }

    def fake_evaluate_answer(**kwargs) -> dict:
        return {
            "score": 8.0,
            "dimension_scores": {"correctness": 8.0, "depth": 8.0, "applied_reasoning": 8.0, "communication": 8.0},
            "rubric_version": "v1",
            "rationale": "Solid answer.",
            "strengths": "Clear reasoning.",
            "gaps": "None notable.",
            "score_variance": 0.0,
            "needs_human_review": False,
            "consistency_check_score": 8.0,
        }

    def fake_generate_report(_session_data: dict) -> dict:
        return {
            "summary": "Strong candidate overall.",
            "overall_score": 8.0,
            "topic_coverage": {"Topic 1": 8.0},
            "strengths": "Deep technical knowledge.",
            "gaps": "Limited leadership examples.",
            "recommendation": "yes",
        }

    monkeypatch.setattr(orchestrator, "extract_text_from_pdf_bytes", fake_extract_text)
    monkeypatch.setattr(orchestrator, "parse_resume", fake_parse_resume)
    monkeypatch.setattr(orchestrator, "generate_question", fake_generate_question)
    monkeypatch.setattr(orchestrator, "evaluate_answer_with_consistency", fake_evaluate_answer)
    monkeypatch.setattr(orchestrator, "generate_report", fake_generate_report)
    return orchestrator


def make_session(client, headers, mock_ai, candidate_name="Test Candidate", role="ai_ml") -> str:
    """Test helper: creates a session via the real HTTP flow (with AI calls mocked) and
    returns its session_id."""
    files = {"resume": ("resume.pdf", b"%PDF-1.4 mock pdf content", "application/pdf")}
    data = {"candidate_name": candidate_name, "role": role}
    res = client.post("/api/sessions", data=data, files=files, headers=headers)
    assert res.status_code == 200, res.text
    return res.json()["session_id"]
