from typing import Iterable, Optional, Union

from models.notification_model import Notification, NotificationTypeEnum


def notify(
    db,
    user_ids: Union[int, Iterable[int]],
    type: NotificationTypeEnum,
    message: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    assignment_id: Optional[int] = None,
) -> None:
    """Queue a Notification for one or more recipients. Does not commit —
    call sites already commit alongside whatever else they changed."""
    ids = [user_ids] if isinstance(user_ids, int) else user_ids
    for user_id in ids:
        db.add(Notification(
            user_id=user_id,
            type=type,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            assignment_id=assignment_id,
        ))
