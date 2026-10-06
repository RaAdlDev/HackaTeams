from typing import Any

from sqlalchemy.orm import Session

from app.enums import NotificationType
from app.models import Notification


def notify(
    db: Session, recipient_id: int, type_: NotificationType, /, **payload: Any
) -> Notification:
    """Persist a notification for `recipient_id` (caller commits).

    Positional-only parameters so payload keys like `user_id` never collide.
    The WebSocket layer will push these live."""
    notification = Notification(user_id=recipient_id, type=type_, payload=payload)
    db.add(notification)
    return notification
