"""add composite index on interview_sessions(user_id, created_at)

Revision ID: f3a9c2e1d8b4
Revises: b7661052c4b1
Create Date: 2026-07-13 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f3a9c2e1d8b4'
down_revision: Union[str, None] = 'b7661052c4b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # list_sessions_for_user filters by user_id and sorts by created_at desc - the
    # existing single-column index on user_id means Postgres still has to sort the
    # matching rows separately at scale. A composite index lets it satisfy both the
    # filter and the ordering directly from the index.
    op.create_index(
        "ix_interview_sessions_user_id_created_at",
        "interview_sessions",
        ["user_id", "created_at"],
    )
    # Redundant now - the composite index above serves user_id-only lookups too,
    # via its leftmost column.
    op.drop_index("ix_interview_sessions_user_id", table_name="interview_sessions")


def downgrade() -> None:
    op.create_index("ix_interview_sessions_user_id", "interview_sessions", ["user_id"])
    op.drop_index("ix_interview_sessions_user_id_created_at", table_name="interview_sessions")
