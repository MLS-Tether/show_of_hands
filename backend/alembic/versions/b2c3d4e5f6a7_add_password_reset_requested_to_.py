"""add password_reset_requested to notificationtypeenum

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE notificationtypeenum ADD VALUE IF NOT EXISTS 'password_reset_requested'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres has no DROP VALUE for enum types; removing a value requires
    # recreating the type, which isn't worth doing for a downgrade path.
    pass
