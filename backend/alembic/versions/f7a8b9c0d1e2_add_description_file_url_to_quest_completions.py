"""add description and file_url to quest_completions

Revision ID: f7a8b9c0d1e2
Revises: c78a7282789d
Create Date: 2026-07-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, Sequence[str], None] = 'c78a7282789d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("quest_completions", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("quest_completions", sa.Column("file_url", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("quest_completions", "file_url")
    op.drop_column("quest_completions", "description")
