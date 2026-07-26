"""add unique constraints on point_transactions and quest_completions

Revision ID: e5f6a7b8c9d1
Revises: c3d4e5f6a7b8
Create Date: 2026-07-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d1'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing data predates the app-level double-award fix this constraint
    # backstops (finalize_submission is supposed to delete the submission-time
    # transaction before inserting the finalized one) — some rows never had
    # the earlier one removed. Repair by keeping only the most recent
    # transaction per (user_id, source, source_id) and backing the superseded
    # amount out of the user's total_points, matching what finalize_submission
    # itself does, before the constraint makes this state impossible to reach.
    conn = op.get_bind()
    superseded = conn.execute(sa.text("""
        SELECT transaction_id, user_id, amount FROM point_transactions pt
        WHERE transaction_id NOT IN (
            SELECT DISTINCT ON (user_id, source, source_id) transaction_id
            FROM point_transactions
            ORDER BY user_id, source, source_id, awarded_at DESC, transaction_id DESC
        )
    """)).fetchall()
    for transaction_id, user_id, amount in superseded:
        conn.execute(
            sa.text("UPDATE users SET total_points = total_points - :amount WHERE user_id = :user_id"),
            {"amount": amount, "user_id": user_id},
        )
        conn.execute(
            sa.text("DELETE FROM point_transactions WHERE transaction_id = :id"),
            {"id": transaction_id},
        )

    op.create_unique_constraint(
        "uq_point_transaction_user_source", "point_transactions", ["user_id", "source", "source_id"]
    )
    op.create_unique_constraint(
        "uq_quest_completion_quest_student", "quest_completions", ["quest_id", "student_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_quest_completion_quest_student", "quest_completions", type_="unique")
    op.drop_constraint("uq_point_transaction_user_source", "point_transactions", type_="unique")
