"""add new_help_request to notificationtypeenum

Revision ID: 91eb2566fe86
Revises: b8e0d1e88eab
Create Date: 2026-07-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '91eb2566fe86'
down_revision: Union[str, Sequence[str], None] = 'b8e0d1e88eab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE notificationtypeenum ADD VALUE IF NOT EXISTS 'new_help_request'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres has no DROP VALUE for enum types; removing a value requires
    # recreating the type, which isn't worth doing for a downgrade path.
    pass
