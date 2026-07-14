"""initial schema

Revision ID: 17d49a43973a
Revises:
Create Date: 2026-07-02 10:48:12.694759

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "17d49a43973a"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

session_status = sa.Enum("created", "active", "completed", name="sessionstatus", create_type=False)


def upgrade() -> None:

    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("candidate_name", sa.String(length=200), nullable=False),
        sa.Column("candidate_email", sa.String(length=200), nullable=True),
        sa.Column("role", sa.String(length=100), nullable=False),
        sa.Column("resume_text", sa.Text(), nullable=False),
        sa.Column("resume_parsed", sa.Text(), nullable=True),
        sa.Column("status", session_status, nullable=True),
        sa.Column("current_question_index", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "questions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), sa.ForeignKey("interview_sessions.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("topic", sa.String(length=200), nullable=True),
        sa.Column("difficulty", sa.String(length=50), nullable=True),
        sa.Column("source_context", sa.Text(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_questions_session_id", "questions", ["session_id"])

    op.create_table(
        "answers",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("question_id", sa.String(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("score_rationale", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_answers_question_id", "answers", ["question_id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), sa.ForeignKey("interview_sessions.id"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("topic_coverage", sa.Text(), nullable=True),
        sa.Column("strengths", sa.Text(), nullable=True),
        sa.Column("gaps", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.String(length=50), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_reports_session_id", "reports", ["session_id"])


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("answers")
    op.drop_table("questions")
    op.drop_table("interview_sessions")
    session_status.drop(op.get_bind(), checkfirst=True)
