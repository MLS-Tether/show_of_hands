"""add assignment_overdue to notificationtypeenum

Revision ID: 35c55fdb28c0
Revises: fda92559ede5
Create Date: 2026-07-10 14:39:09.189462

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '35c55fdb28c0'
down_revision: Union[str, Sequence[str], None] = 'fda92559ede5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE notificationtypeenum ADD VALUE IF NOT EXISTS 'assignment_overdue'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres has no DROP VALUE for enum types; removing a value requires
    # recreating the type, which isn't worth doing for a downgrade path.
    pass
