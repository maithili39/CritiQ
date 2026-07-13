"""phase1 auth security fields

Revision ID: 8e4b6c1f2d7a
Revises: 2372897d521a
Create Date: 2026-07-02 14:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8e4b6c1f2d7a"
down_revision: Union[str, None] = "2372897d521a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column(
        "users",
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("locked_until", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("password_reset_token_hash", sa.String(), nullable=True))
    op.add_column("users", sa.Column("password_reset_token_expires_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("email_verification_token_hash", sa.String(), nullable=True))
    op.add_column("users", sa.Column("email_verification_token_expires_at", sa.DateTime(), nullable=True))

    op.alter_column("users", "is_admin", server_default=None)
    op.alter_column("users", "email_verified", server_default=None)
    op.alter_column("users", "failed_login_attempts", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "email_verification_token_expires_at")
    op.drop_column("users", "email_verification_token_hash")
    op.drop_column("users", "password_reset_token_expires_at")
    op.drop_column("users", "password_reset_token_hash")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "is_admin")
