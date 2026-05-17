from sqlalchemy.orm import Session

from app.models.notification import Notification


def create_notification(
    db: Session,
    *,
    user_id: int,
    type: str,
    title: str,
    body: str,
    related_task_id: int | None = None,
    related_comment_id: int | None = None,
    related_signal_id: int | None = None,
    related_signal_feedback_id: int | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        related_task_id=related_task_id,
        related_comment_id=related_comment_id,
        related_signal_id=related_signal_id,
        related_signal_feedback_id=related_signal_feedback_id,
    )
    db.add(notification)
    db.flush()
    return notification


def list_notifications(
    db: Session,
    *,
    user_id: int,
    unread_only: bool = False,
    limit: int = 50,
) -> list[Notification]:
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.read_at.is_(None))
    return (
        query.order_by(Notification.created_at.desc()).limit(limit).all()
    )


def unread_count(db: Session, *, user_id: int) -> int:
    return (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        .count()
    )


def mark_read(db: Session, *, notification_id: int) -> Notification | None:
    from sqlalchemy import func

    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id)
        .first()
    )
    if not notification:
        return None
    if notification.read_at is None:
        notification.read_at = func.now()
        db.flush()
    return notification


def mark_all_read(db: Session, *, user_id: int) -> int:
    from sqlalchemy import func

    rows = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        .update({Notification.read_at: func.now()}, synchronize_session=False)
    )
    return rows
