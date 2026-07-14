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
    generated_at = Column(DateTime, default=lambda: datetime.now(UTC))

    session = relationship("InterviewSession", back_populates="report")
