"""The matching engine: rank candidates by how many tags they share with a reference tag set.

Score = number of overlapping tag ids (SQL COUNT over an outer join, so candidates with
no overlap still appear, ranked last, instead of new users getting an empty feed)."""
from collections.abc import Sequence

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.enums import ProjectStatus
from app.models import (
    Application,
    Profile,
    Project,
    ProjectMember,
    ProjectTagLink,
    Swipe,
    Tag,
    User,
    UserTagLink,
)


def user_tag_ids(db: Session, user_id: int) -> list[int]:
    return list(db.scalars(select(UserTagLink.tag_id).where(UserTagLink.user_id == user_id)))


def project_tag_ids(db: Session, project_id: int) -> list[int]:
    return list(db.scalars(select(ProjectTagLink.tag_id).where(ProjectTagLink.project_id == project_id)))


def browse_users(
    db: Session,
    me: User,
    *,
    reference_tag_ids: Sequence[int],
    region: str | None = None,
    q: str | None = None,
    filter_tag_ids: Sequence[int] = (),
    min_overlap: int = 0,
    exclude_user_ids: Sequence[int] = (),
    limit: int = 20,
    offset: int = 0,
) -> list[tuple[Profile, int]]:
    seen = select(Swipe.target_user_id).where(
        Swipe.user_id == me.id, Swipe.target_user_id.is_not(None)
    )
    overlap = func.count(UserTagLink.tag_id)

    stmt = (
        select(Profile, overlap.label("overlap"))
        .join(User, User.id == Profile.user_id)
        .outerjoin(
            UserTagLink,
            and_(
                UserTagLink.user_id == Profile.user_id,
                UserTagLink.tag_id.in_(list(reference_tag_ids)),
            ),
        )
        .where(User.is_active.is_(True), Profile.user_id != me.id, Profile.user_id.not_in(seen))
        .group_by(Profile.id)
        .order_by(overlap.desc(), Profile.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if exclude_user_ids:
        stmt = stmt.where(Profile.user_id.not_in(list(exclude_user_ids)))
    if region:
        stmt = stmt.where(Profile.region.icontains(region, autoescape=True))
    if q:
        stmt = stmt.where(
            or_(
                Profile.username.icontains(q, autoescape=True),
                Profile.bio.icontains(q, autoescape=True),
            )
        )
    if filter_tag_ids:
        stmt = stmt.where(
            Profile.user_id.in_(
                select(UserTagLink.user_id).where(UserTagLink.tag_id.in_(list(filter_tag_ids)))
            )
        )
    if min_overlap > 0:
        stmt = stmt.having(overlap >= min_overlap)

    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def browse_projects(
    db: Session,
    me: User,
    *,
    reference_tag_ids: Sequence[int],
    region: str | None = None,
    q: str | None = None,
    filter_tag_ids: Sequence[int] = (),
    min_overlap: int = 0,
    limit: int = 20,
    offset: int = 0,
) -> list[tuple[Project, int]]:
    seen = select(Swipe.target_project_id).where(
        Swipe.user_id == me.id, Swipe.target_project_id.is_not(None)
    )
    applied = select(Application.project_id).where(Application.applicant_id == me.id)
    overlap = func.count(ProjectTagLink.tag_id)

    stmt = (
        select(Project, overlap.label("overlap"))
        .outerjoin(
            ProjectTagLink,
            and_(
                ProjectTagLink.project_id == Project.id,
                ProjectTagLink.tag_id.in_(list(reference_tag_ids)),
            ),
        )
        .where(
            Project.status == ProjectStatus.OPEN,
            Project.owner_id != me.id,
            Project.id.not_in(seen),
            Project.id.not_in(applied),
        )
        .group_by(Project.id)
        .order_by(overlap.desc(), Project.created_at.desc(), Project.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if region:
        stmt = stmt.where(Project.region.icontains(region, autoescape=True))
    if q:
        stmt = stmt.where(
            or_(
                Project.title.icontains(q, autoescape=True),
                Project.description.icontains(q, autoescape=True),
            )
        )
    if filter_tag_ids:
        stmt = stmt.where(
            Project.id.in_(
                select(ProjectTagLink.project_id).where(
                    ProjectTagLink.tag_id.in_(list(filter_tag_ids))
                )
            )
        )
    if min_overlap > 0:
        stmt = stmt.having(overlap >= min_overlap)

    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def shared_tags_for_users(
    db: Session, user_ids: Sequence[int], tag_ids: Sequence[int]
) -> dict[int, list[Tag]]:
    result: dict[int, list[Tag]] = {uid: [] for uid in user_ids}
    if not user_ids or not tag_ids:
        return result
    rows = db.execute(
        select(UserTagLink.user_id, Tag)
        .join(Tag, Tag.id == UserTagLink.tag_id)
        .where(UserTagLink.user_id.in_(list(user_ids)), UserTagLink.tag_id.in_(list(tag_ids)))
        .order_by(Tag.name)
    ).all()
    for user_id, tag in rows:
        result[user_id].append(tag)
    return result


def shared_tags_for_projects(
    db: Session, project_ids: Sequence[int], tag_ids: Sequence[int]
) -> dict[int, list[Tag]]:
    result: dict[int, list[Tag]] = {pid: [] for pid in project_ids}
    if not project_ids or not tag_ids:
        return result
    rows = db.execute(
        select(ProjectTagLink.project_id, Tag)
        .join(Tag, Tag.id == ProjectTagLink.tag_id)
        .where(
            ProjectTagLink.project_id.in_(list(project_ids)),
            ProjectTagLink.tag_id.in_(list(tag_ids)),
        )
        .order_by(Tag.name)
    ).all()
    for project_id, tag in rows:
        result[project_id].append(tag)
    return result


def project_member_ids(db: Session, project_id: int) -> list[int]:
    return list(db.scalars(select(ProjectMember.user_id).where(ProjectMember.project_id == project_id)))
