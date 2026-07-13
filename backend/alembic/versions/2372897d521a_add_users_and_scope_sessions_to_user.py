"""add users and scope sessions to user

Revision ID: 2372897d521a
Revises: 62c045179476
Create Date: 2026-07-02 11:30:39.003576

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2372897d521a'
down_revision: Union[str, None] = '62c045179476'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Session-scoped access tokens are replaced by proper user accounts.
    op.drop_column("interview_sessions", "access_token")

    op.add_column("interview_sessions", sa.Column("user_id", sa.String(), nullable=True))
    op.create_index("ix_interview_sessions_user_id", "interview_sessions", ["user_id"])
    op.create_foreign_key(
        "fk_interview_sessions_user_id", "interview_sessions", "users", ["user_id"], ["id"]
    )
    # No existing rows to backfill against yet (unreleased project) — safe to enforce now.
    op.alter_column("interview_sessions", "user_id", nullable=False)


def downgrade() -> None:
    op.drop_constraint("fk_interview_sessions_user_id", "interview_sessions", type_="foreignkey")
    op.drop_index("ix_interview_sessions_user_id", table_name="interview_sessions")
    op.drop_column("interview_sessions", "user_id")

    op.add_column("interview_sessions", sa.Column("access_token", sa.String(), nullable=True))

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
