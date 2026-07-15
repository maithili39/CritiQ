"""role profiles, hiring outcomes, session integrity summary

Adds, in one migration:
- custom_roles.persona / difficulty_guide  (item: functional custom roles)
- interview_sessions.outcome / outcome_note / outcome_at  (item: feedback loop)
- reports.integrity_summary  (item: anti-cheating signal fusion)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-15 08:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Functional custom roles ---
    op.add_column("custom_roles", sa.Column("persona", sa.Text(), nullable=True))
    op.add_column("custom_roles", sa.Column("difficulty_guide", sa.Text(), nullable=True))

    # --- Recruiter hiring-outcome feedback (ground truth for score calibration) ---
    op.add_column("interview_sessions", sa.Column("outcome", sa.String(50), nullable=True))
    op.add_column("interview_sessions", sa.Column("outcome_note", sa.Text(), nullable=True))
    op.add_column("interview_sessions", sa.Column("outcome_at", sa.DateTime(), nullable=True))

    # --- Fused session-level integrity assessment ---
    op.add_column("reports", sa.Column("integrity_summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "integrity_summary")
    op.drop_column("interview_sessions", "outcome_at")
    op.drop_column("interview_sessions", "outcome_note")
    op.drop_column("interview_sessions", "outcome")
    op.drop_column("custom_roles", "difficulty_guide")
    op.drop_column("custom_roles", "persona")
