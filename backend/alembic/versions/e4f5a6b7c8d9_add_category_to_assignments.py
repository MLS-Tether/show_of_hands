"""add category to assignments

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-07-16 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, Sequence[str], None] = 'd3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    assignment_category = sa.Enum('homework', 'quizzes', 'tests', name='assignmentcategoryenum')
    assignment_category.create(op.get_bind())
    op.add_column(
        'assignments',
        sa.Column('category', assignment_category, nullable=False, server_default='homework'),
    )
    op.alter_column('assignments', 'category', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('assignments', 'category')
    sa.Enum(name='assignmentcategoryenum').drop(op.get_bind())
