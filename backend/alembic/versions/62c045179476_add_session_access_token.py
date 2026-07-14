"""add session access token

Revision ID: 62c045179476
Revises: 17d49a43973a
Create Date: 2026-07-02 11:09:51.074988

"""
import secrets
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '62c045179476'
down_revision: str | None = '17d49a43973a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add nullable first so this doesn't fail against any pre-existing rows,
    # backfill a random token for each, then enforce NOT NULL.
    op.add_column("interview_sessions", sa.Column("access_token", sa.String(), nullable=True))

    conn = op.get_bind()
    session_ids = [row[0] for row in conn.execute(sa.text("SELECT id FROM interview_sessions"))]
    for session_id in session_ids:
        conn.execute(
            sa.text("UPDATE interview_sessions SET access_token = :token WHERE id = :id"),
            {"token": secrets.token_urlsafe(32), "id": session_id},
        )

    op.alter_column("interview_sessions", "access_token", nullable=False)


def downgrade() -> None:
    op.drop_column("interview_sessions", "access_token")
