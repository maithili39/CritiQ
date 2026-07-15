"""add anti-cheating fields and custom roles table

Revision ID: a1b2c3d4e5f6
Revises: b7661052c4b1
Create Date: 2026-07-15 07:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "b7661052c4b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Anti-cheating telemetry columns on answers ---
    op.add_column("answers", sa.Column("response_time_ms", sa.Integer(), nullable=True))
    op.add_column("answers", sa.Column("paste_detected", sa.Boolean(), nullable=True, server_default=sa.false()))
    op.add_column("answers", sa.Column("tab_switch_count", sa.Integer(), nullable=True, server_default="0"))
    op.add_column("answers", sa.Column("integrity_flags", sa.Text(), nullable=True))
    op.add_column("answers", sa.Column("camera_snapshot", sa.Text(), nullable=True))

    # Remove server defaults (columns are nullable — only used for new rows going forward)
    op.alter_column("answers", "paste_detected", server_default=None)
    op.alter_column("answers", "tab_switch_count", server_default=None)

    # --- Custom roles table ---
    op.create_table(
        "custom_roles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("topics", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_custom_roles_slug", "custom_roles", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_custom_roles_slug", table_name="custom_roles")
    op.drop_table("custom_roles")

    op.drop_column("answers", "camera_snapshot")
    op.drop_column("answers", "integrity_flags")
    op.drop_column("answers", "tab_switch_count")
    op.drop_column("answers", "paste_detected")
    op.drop_column("answers", "response_time_ms")
