"""add new_class_request to notificationtypeenum

Revision ID: 4edfc8ebfebb
Revises: f6a7b8c9d0e2
Create Date: 2026-07-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4edfc8ebfebb'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE notificationtypeenum ADD VALUE IF NOT EXISTS 'new_class_request'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres has no DROP VALUE for enum types; removing a value requires
    # recreating the type, which isn't worth doing for a downgrade path.
    pass
