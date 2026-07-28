"""add unenroll notification types to notificationtypeenum

Revision ID: c78a7282789d
Revises: 89a38094bf52
Create Date: 2026-07-26 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c78a7282789d'
down_revision: Union[str, Sequence[str], None] = '89a38094bf52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE notificationtypeenum ADD VALUE IF NOT EXISTS 'new_unenroll_request'")
    op.execute("ALTER TYPE notificationtypeenum ADD VALUE IF NOT EXISTS 'unenroll_request_approved'")
    op.execute("ALTER TYPE notificationtypeenum ADD VALUE IF NOT EXISTS 'unenroll_request_rejected'")
    op.execute("ALTER TYPE notificationtypeenum ADD VALUE IF NOT EXISTS 'removed_from_section'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres has no DROP VALUE for enum types; removing a value requires
    # recreating the type, which isn't worth doing for a downgrade path.
    pass
