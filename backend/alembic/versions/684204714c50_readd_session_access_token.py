"""re-add interview_sessions.access_token

Revision ID: 684204714c50
Revises: f3a9c2e1d8b4
Create Date: 2026-07-14 22:15:00.000000

Migration 2372897d521a dropped this column when session-scoped access was
replaced by user accounts, but candidate-facing invite links
(app/models/session.py:access_token, app/api/deps.py:get_session_by_access_token,
POST /sessions/{id}/invite/send) still require it on the model. The column was
never re-added, so every session-creation request has failed against a
freshly-migrated database with UndefinedColumn. The test suite didn't catch
this because conftest.py builds its schema via Base.metadata.create_all()
rather than by running the Alembic chain.
"""

import secrets
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "684204714c50"
down_revision: str | None = "f3a9c2e1d8b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("interview_sessions", sa.Column("access_token", sa.String(), nullable=True))

    conn = op.get_bind()
    session_ids = [row[0] for row in conn.execute(sa.text("SELECT id FROM interview_sessions"))]
    for session_id in session_ids:
        conn.execute(
            sa.text("UPDATE interview_sessions SET access_token = :token WHERE id = :id"),
            {"token": secrets.token_urlsafe(32), "id": session_id},
        )

    op.alter_column("interview_sessions", "access_token", nullable=False)
    op.create_index("ix_interview_sessions_access_token", "interview_sessions", ["access_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_interview_sessions_access_token", table_name="interview_sessions")
    op.drop_column("interview_sessions", "access_token")
