"""add shop_items and student_inventory tables

Revision ID: 225d02b9066f
Revises: a1b2c3d4e5f6
Create Date: 2026-07-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '225d02b9066f'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE transactionsourceenum ADD VALUE IF NOT EXISTS 'shop_purchase'")

    op.create_table(
        'shop_items',
        sa.Column('item_id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'item_type',
            sa.Enum('avatar_base', 'avatar_accessory', 'badge', 'theme', name='shopitemtypeenum'),
            nullable=False,
        ),
        sa.Column('cost', sa.Integer(), nullable=False),
        sa.Column('image_url', sa.String(), nullable=False),
        sa.Column('theme_key', sa.String(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'student_inventory',
        sa.Column('inventory_id', sa.Integer(), primary_key=True),
        sa.Column('student_id', sa.Integer(), sa.ForeignKey('users.user_id'), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('shop_items.item_id'), nullable=False),
        sa.Column('is_equipped', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('purchased_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('student_id', 'item_id', name='uq_inventory_student_item'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('student_inventory')
    op.drop_table('shop_items')
    sa.Enum(name='shopitemtypeenum').drop(op.get_bind())
    # Postgres has no DROP VALUE for enum types; removing 'shop_purchase'
    # requires recreating the type, which isn't worth doing for a downgrade path.