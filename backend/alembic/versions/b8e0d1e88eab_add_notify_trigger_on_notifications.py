"""add pg_notify trigger on notifications insert

Revision ID: b8e0d1e88eab
Revises: 35c55fdb28c0
Create Date: 2026-07-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8e0d1e88eab'
down_revision: Union[str, Sequence[str], None] = '35c55fdb28c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CHANNEL_NAME = "user_notifications_channel"


def upgrade() -> None:
    """Upgrade schema."""
    # Fires on every insert into notifications regardless of which code path
    # created it (existing or future), so the app-level WebSocket relay never
    # has to be manually wired into each notification-creation call site.
    op.execute(f"""
        CREATE OR REPLACE FUNCTION notify_new_notification() RETURNS trigger AS $$
        BEGIN
            PERFORM pg_notify(
                '{CHANNEL_NAME}',
                json_build_object(
                    'user_id', NEW.user_id,
                    'notification_id', NEW.notification_id
                )::text
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER notifications_notify_trigger
        AFTER INSERT ON notifications
        FOR EACH ROW EXECUTE FUNCTION notify_new_notification();
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS notifications_notify_trigger ON notifications;")
    op.execute("DROP FUNCTION IF EXISTS notify_new_notification();")
