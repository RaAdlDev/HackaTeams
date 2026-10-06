from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select

from app.deps import CurrentUser, DbSession
from app.enums import ProjectStatus
from app.models import Project, ProjectRole, ProjectTagLink
from app.schemas.project import (
    BrowseProjectOut,
    ProjectCreate,
    ProjectDetailOut,
    ProjectSummaryOut,
    ProjectUpdate,
    RoleIn,
    RoleOut,
)
from app.schemas.tag import TagOut
from app.services import matching
from app.services.tags import ensure_tags_exist

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_owned_project(db, project_id: int, user) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if project.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the project owner can do this")
    return project


def _sync_tags(project: Project, tag_ids: list[int]) -> None:
    wanted = set(tag_ids)
    existing = {link.tag_id: link for link in project.tag_links}
    for tag_id, link in existing.items():
        if tag_id not in wanted:
            project.tag_links.remove(link)
    for tag_id in wanted - existing.keys():
        project.tag_links.append(ProjectTagLink(tag_id=tag_id))


@router.post("/", response_model=ProjectDetailOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, user: CurrentUser, db: DbSession):
    """Publish a project: scope, required roles, timeline and the tags it needs."""
    ensure_tags_exist(db, payload.tag_ids)
    project = Project(
        owner_id=user.id,
        title=payload.title,
        description=payload.description,
        region=payload.region,
        hackathon_name=payload.hackathon_name,
        start_date=payload.start_date,
        deadline=payload.deadline,
        tag_links=[ProjectTagLink(tag_id=t) for t in set(payload.tag_ids)],
        roles=[ProjectRole(**r.model_dump()) for r in payload.roles],
    )
    db.add(project)
    db.commit()
    return project


@router.get("/feed", response_model=list[ProjectSummaryOut])
def project_feed(
    user: CurrentUser,
    db: DbSession,
    region: str | None = Query(default=None, max_length=100),
    q: str | None = Query(default=None, max_length=100),
    tag_ids: list[int] = Query(default=[]),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    """Chronological board of all open projects (newest first), paginated."""
    stmt = (
        select(Project)
        .where(Project.status == ProjectStatus.OPEN)
        .order_by(Project.created_at.desc(), Project.id.desc())
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
    if tag_ids:
        stmt = stmt.where(
            Project.id.in_(
                select(ProjectTagLink.project_id).where(ProjectTagLink.tag_id.in_(tag_ids))
            )
        )
    return db.scalars(stmt).unique().all()


@router.get("/browse", response_model=list[BrowseProjectOut])
def browse_projects(
    user: CurrentUser,
    db: DbSession,
    region: str | None = Query(default=None, max_length=100),
    q: str | None = Query(default=None, max_length=100),
    tag_ids: list[int] = Query(default=[], description="Only projects having ANY of these tags"),
    min_overlap: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    """The 'swipe' feed of projects, ranked by tags shared with the current user.

    Excludes your own projects, ones you've swiped on, and ones you've applied to."""
    reference = matching.user_tag_ids(db, user.id)
    rows = matching.browse_projects(
        db,
        user,
        reference_tag_ids=reference,
        region=region,
        q=q,
        filter_tag_ids=tag_ids,
        min_overlap=min_overlap,
        limit=limit,
        offset=offset,
    )
    shared = matching.shared_tags_for_projects(db, [p.id for p, _ in rows], reference)
    return [
        BrowseProjectOut(
            project=ProjectSummaryOut.model_validate(project),
            match_score=score,
            shared_tags=[TagOut.model_validate(t) for t in shared[project.id]],
        )
        for project, score in rows
    ]


@router.get("/mine", response_model=list[ProjectSummaryOut])
def my_projects(user: CurrentUser, db: DbSession):
    stmt = select(Project).where(Project.owner_id == user.id).order_by(Project.created_at.desc())
    return db.scalars(stmt).unique().all()


@router.get("/{project_id}", response_model=ProjectDetailOut)
def read_project(project_id: int, db: DbSession, _: CurrentUser):
    """Full scope, required roles and current team members."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectDetailOut)
def update_project(project_id: int, payload: ProjectUpdate, user: CurrentUser, db: DbSession):
    project = _get_owned_project(db, project_id, user)
    data = payload.model_dump(exclude_unset=True)
    tag_ids = data.pop("tag_ids", None)

    for required in ("title", "description", "status"):
        if required in data and data[required] is None:
            raise HTTPException(422, f"{required} cannot be null")
    for field, value in data.items():
        setattr(project, field, value)
    if project.start_date and project.deadline and project.deadline < project.start_date:
        raise HTTPException(422, "deadline must not be before start_date")

    if tag_ids is not None:
        ensure_tags_exist(db, tag_ids)
        _sync_tags(project, tag_ids)
    db.commit()
    return project


@router.post("/{project_id}/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def add_role(project_id: int, payload: RoleIn, user: CurrentUser, db: DbSession):
    project = _get_owned_project(db, project_id, user)
    role = ProjectRole(project_id=project.id, **payload.model_dump())
    db.add(role)
    db.commit()
    return role


@router.delete("/{project_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(project_id: int, role_id: int, user: CurrentUser, db: DbSession):
    project = _get_owned_project(db, project_id, user)
    role = db.get(ProjectRole, role_id)
    if role is None or role.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found")
    db.delete(role)
    db.commit()
