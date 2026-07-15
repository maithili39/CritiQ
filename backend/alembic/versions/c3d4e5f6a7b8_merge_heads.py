"""merge access_token and rubric-review-flag heads

The tree branched at b7661052c4b1 into the access_token re-add line
(684204714c50) and the anti-cheating/rubric line (b2c3d4e5f6a7). This is an
empty merge so `alembic upgrade head` has a single target again.

Revision ID: c3d4e5f6a7b8
Revises: 684204714c50, b2c3d4e5f6a7
Create Date: 2026-07-15 08:15:00.000000

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: tuple[str, ...] = ("684204714c50", "b2c3d4e5f6a7")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
