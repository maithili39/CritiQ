"""add session background processing fields

Revision ID: b7661052c4b1
Revises: 8e4b6c1f2d7a
Create Date: 2026-07-13 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7661052c4b1"
down_revision: str | None = "8e4b6c1f2d7a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "interview_sessions",
        sa.Column("is_processing", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("interview_sessions", sa.Column("processing_error", sa.Text(), nullable=True))
    op.alter_column("interview_sessions", "is_processing", server_default=None)


def downgrade() -> None:
    op.drop_column("interview_sessions", "processing_error")
    op.drop_column("interview_sessions", "is_processing")
