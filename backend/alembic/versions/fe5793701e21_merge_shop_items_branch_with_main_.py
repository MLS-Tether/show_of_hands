"""merge shop_items branch with main migration chain

Revision ID: fe5793701e21
Revises: 225d02b9066f, f7a8b9c0d1e2
Create Date: 2026-07-28 12:01:09.768407

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fe5793701e21'
down_revision: Union[str, Sequence[str], None] = ('225d02b9066f', 'f7a8b9c0d1e2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
