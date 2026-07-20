"""make full_name required on users

Revision ID: d4e5f6a7b8c9
Revises: c9d1e2f3a4b5
Create Date: 2026-07-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c9d1e2f3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing rows predate this field — backfill with username so the
    # NOT NULL constraint below doesn't reject them.
    op.execute("UPDATE users SET full_name = username WHERE full_name IS NULL")
    op.alter_column('users', 'full_name', existing_type=sa.String(), nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'full_name', existing_type=sa.String(), nullable=True)
