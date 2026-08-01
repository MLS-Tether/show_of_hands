"""add badge_rules table

Revision ID: a4b5c6d7e8f9
Revises: fe5793701e21
Create Date: 2026-08-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4b5c6d7e8f9'
down_revision: Union[str, Sequence[str], None] = 'fe5793701e21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "badge_rules",
        sa.Column("badge_rule_id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("shop_items.item_id"), nullable=False, unique=True),
        sa.Column(
            "criteria_type",
            sa.Enum(
                "first_quest",
                "quest_streak",
                "event_count",
                "lifetime_points",
                "quest_total_count",
                "section_grade_threshold",
                name="badgerulecriteriaenum",
            ),
            nullable=False,
        ),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("badge_rules")
    op.execute("DROP TYPE IF EXISTS badgerulecriteriaenum")
