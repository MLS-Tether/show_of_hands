"""add unenroll_requests table

Revision ID: 89a38094bf52
Revises: 4edfc8ebfebb
Create Date: 2026-07-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89a38094bf52'
down_revision: Union[str, Sequence[str], None] = '4edfc8ebfebb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'unenroll_requests',
        sa.Column('unenroll_request_id', sa.Integer(), nullable=False),
        sa.Column('section_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('requested_by', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('pending', 'approved', 'rejected', 'cancelled', name='unenrollrequeststatusenum'),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['section_id'], ['sections.section_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('unenroll_request_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('unenroll_requests')
    sa.Enum(name='unenrollrequeststatusenum').drop(op.get_bind(), checkfirst=True)
