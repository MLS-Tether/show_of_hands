"""add unique constraint on submissions (assignment_id, student_id)

Revision ID: a1b2c3d4e5f6
Revises: d4e5f6a7b8c9
Create Date: 2026-07-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(
        'uq_submission_assignment_student', 'submissions', ['assignment_id', 'student_id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_submission_assignment_student', 'submissions', type_='unique')
