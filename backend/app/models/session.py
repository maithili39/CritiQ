import enum
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class SessionStatus(enum.StrEnum):
    created = "created"
    active = "active"
    completed = "completed"


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # No standalone index=True here - the composite index below (user_id, created_at)
    # already covers user_id-only lookups via its leftmost column, so a separate
    # single-column index would just be redundant write overhead.
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    candidate_name = Column(String(200), nullable=False)
    candidate_email = Column(String(200), nullable=True)
    role = Column(String(100), nullable=False)
    # Bearer secret for the candidate invite link (/take/{id}?token=...) — lets an
    # unauthenticated candidate act on their own session without a user account.
    access_token = Column(String, nullable=False, unique=True, index=True, default=lambda: secrets.token_urlsafe(32))
    resume_text = Column(Text, nullable=False)
    resume_parsed = Column(Text, nullable=True)  # JSON: skills, tech, experience_level
    status = Column(Enum(SessionStatus), default=SessionStatus.created)
    current_question_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime, nullable=True)

    # Candidate-flow answer submission runs scoring + next-question generation (or
    # report generation, if it was the last question) in a background task instead
    # of blocking the HTTP request. The frontend polls this session and waits for
    # is_processing to clear rather than waiting on the Claude round-trip directly.
    is_processing = Column(Boolean, nullable=False, default=False)
    processing_error = Column(Text, nullable=True)

    # --- Recruiter hiring-outcome feedback (ground truth for score calibration) ---
    # Filled in by the recruiter AFTER a real interview/decision, so we can measure
    # whether the AI's overall_score actually predicted good hires. One of:
    # hired_strong / hired / rejected / no_show / null (not yet recorded).
    outcome = Column(String(50), nullable=True)
    outcome_note = Column(Text, nullable=True)
    outcome_at = Column(DateTime, nullable=True)

    __table_args__ = (
        # Satisfies list_sessions_for_user's filter-by-user_id + order-by-created_at
        # directly from the index at scale, instead of a separate sort step.
        Index("ix_interview_sessions_user_id_created_at", "user_id", "created_at"),
    )

    user = relationship("User", back_populates="sessions")
    questions = relationship("Question", back_populates="session", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="session", uselist=False, cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("interview_sessions.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    topic = Column(String(200), nullable=True)
    difficulty = Column(String(50), nullable=True)  # beginner / intermediate / advanced
    source_context = Column(Text, nullable=True)  # retrieved RAG chunks used
    order = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    session = relationship("InterviewSession", back_populates="questions")
    answer = relationship("Answer", back_populates="question", uselist=False, cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(String, ForeignKey("questions.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    score = Column(Float, nullable=True)  # 0-10, evaluated by LLM
    score_rationale = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=lambda: datetime.now(UTC))

    # --- Anti-cheating telemetry fields ---
    # Time (ms) from question first rendered to answer submission.
    response_time_ms = Column(Integer, nullable=True)
    # True if the candidate used paste (Ctrl+V / right-click paste) in the answer box.
    paste_detected = Column(Boolean, nullable=True, default=False)
    # Number of times the candidate switched away from the tab/window during this question.
    tab_switch_count = Column(Integer, nullable=True, default=0)
    # JSON blob: computed integrity assessment e.g. {"suspicious": true, "reasons": ["paste_detected"]}
    integrity_flags = Column(Text, nullable=True)
    # Base64-encoded JPEG still from candidate's webcam captured at answer submission.
    camera_snapshot = Column(Text, nullable=True)

    # True when the two independent rubric-scoring passes (see
    # evaluate_answer_with_consistency) disagreed by more than the variance
    # threshold — a signal that the LLM judge itself was uncertain, not just an
    # anti-cheating telemetry flag. Queryable directly for a recruiter review queue.
    needs_human_review = Column(Boolean, nullable=True, default=False)

    question = relationship("Question", back_populates="answer")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("interview_sessions.id"), nullable=False, index=True)
    summary = Column(Text, nullable=True)
    overall_score = Column(Float, nullable=True)
    topic_coverage = Column(Text, nullable=True)  # JSON: {topic: score}
    strengths = Column(Text, nullable=True)
    gaps = Column(Text, nullable=True)
    recommendation = Column(String(50), nullable=True)  # strong_yes / yes / maybe / no
    # JSON: fused session-level integrity assessment computed at report time from
    # all answers' telemetry (response-time distribution, paste/tab signals). Shape:
    # {"confidence": 0-100, "risk_level": "low|medium|high", "signals": [...]}
    integrity_summary = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=lambda: datetime.now(UTC))

    session = relationship("InterviewSession", back_populates="report")


class CustomRole(Base):
    """
    Recruiter-defined interview role tracks beyond the built-in ai_ml / data_science defaults.
    Slug is the stable machine-readable identifier used in sessions and ChromaDB collections.
    """
    __tablename__ = "custom_roles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String(100), nullable=False, unique=True, index=True)
    label = Column(String(200), nullable=False)           # Human-readable display name
    description = Column(Text, nullable=True)             # Short description shown in Setup UI
    topics = Column(Text, nullable=True)                  # JSON array of topic tags for display
    # Interviewer persona + difficulty rubric text used to steer question generation.
    # Populated at creation (LLM-generated from label/description/topics if the
    # recruiter doesn't supply them), so custom roles drive prompting the same way
    # built-in roles do instead of falling back to a generic persona string.
    persona = Column(Text, nullable=True)
    difficulty_guide = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
