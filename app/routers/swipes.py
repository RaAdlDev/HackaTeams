from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.enums import NotificationType, ProjectStatus, SwipeAction
from app.models import Project, Swipe, User
from app.schemas.social import SwipeCreate, SwipeOut
from app.services.notifications import notify

router = APIRouter(prefix="/swipes", tags=["matching"])


@router.post("", response_model=SwipeOut)
def swipe(payload: SwipeCreate, user: CurrentUser, db: DbSession):
    """Like or pass on a developer or a project. Swiping again changes your answer.

    A *match* happens when two developers like each other, or when you like a project
    whose owner has already liked you. Both sides get a `new_match` notification."""
    target_user: User | None = None
    project: Project | None = None

    if payload.target_user_id is not None:
        if payload.target_user_id == user.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot swipe on yourself")
        target_user = db.get(User, payload.target_user_id)
        if target_user is None or not target_user.is_active:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        existing = db.scalar(
            select(Swipe).where(Swipe.user_id == user.id, Swipe.target_user_id == target_user.id)
        )
    else:
        project = db.get(Project, payload.target_project_id)
        if project is None or project.status != ProjectStatus.OPEN:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
        if project.owner_id == user.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot swipe on your own project")
        existing = db.scalar(
            select(Swipe).where(Swipe.user_id == user.id, Swipe.target_project_id == project.id)
        )

    was_like = existing is not None and existing.action == SwipeAction.LIKE
    if existing:
        existing.action = payload.action
    else:
        db.add(
            Swipe(
                user_id=user.id,
                target_user_id=payload.target_user_id,
                target_project_id=payload.target_project_id,
                action=payload.action,
            )
        )

    matched = False
    if payload.action == SwipeAction.LIKE:
        if target_user is not None:
            matched = (
                db.scalar(
                    select(Swipe.id).where(
                        Swipe.user_id == target_user.id,
                        Swipe.target_user_id == user.id,
                        Swipe.action == SwipeAction.LIKE,
                    )
                )
                is not None
            )
            if matched and not was_like:
                for recipient, other in ((user, target_user), (target_user, user)):
                    notify(db, recipient.id, NotificationType.NEW_MATCH,
                           user_id=other.id, username=other.username)
        else:
            owner_likes_back = (
                db.scalar(
                    select(Swipe.id).where(
                        Swipe.user_id == project.owner_id,
                        Swipe.target_user_id == user.id,
                        Swipe.action == SwipeAction.LIKE,
                    )
                )
                is not None
            )
            matched = owner_likes_back
            if not was_like:
                if matched:
                    notify(db, user.id, NotificationType.NEW_MATCH,
                           user_id=project.owner_id, username=project.owner.username,
                           project_id=project.id, project_title=project.title)
                    notify(db, project.owner_id, NotificationType.NEW_MATCH,
                           user_id=user.id, username=user.username,
                           project_id=project.id, project_title=project.title)
                else:
                    notify(db, project.owner_id, NotificationType.PROJECT_INTEREST,
                           project_id=project.id, project_title=project.title,
                           user_id=user.id, username=user.username)
    db.commit()
    return SwipeOut(action=payload.action, matched=matched)
