"""add url to assignments

Revision ID: a3f7c1d2e4b5
Revises: 91eb2566fe86
Create Date: 2026-07-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f7c1d2e4b5'
down_revision: Union[str, Sequence[str], None] = '91eb2566fe86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('assignments', sa.Column('url', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('assignments', 'url')
