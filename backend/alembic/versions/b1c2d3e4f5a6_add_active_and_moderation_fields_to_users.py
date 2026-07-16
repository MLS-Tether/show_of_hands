"""add active and moderation fields to users

Revision ID: b1c2d3e4f5a6
Revises: a3f7c1d2e4b5
Create Date: 2026-07-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a3f7c1d2e4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )
    op.alter_column('users', 'is_active', server_default=None)
    op.add_column('users', sa.Column('rejection_reason', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('signup_note', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'signup_note')
    op.drop_column('users', 'last_active_at')
    op.drop_column('users', 'rejection_reason')
    op.drop_column('users', 'is_active')
