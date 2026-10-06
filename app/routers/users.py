from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.deps import CurrentUser, DbSession
from app.models import HackathonEntry, PastProject, Profile, Project, User, UserTagLink
from app.schemas.tag import TagOut
from app.schemas.user import BrowseUserOut, MeOut, ProfileOut, ProfileUpdate
from app.services import matching
from app.services.tags import ensure_tags_exist

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=MeOut)
def read_me(user: CurrentUser):
    return user


@router.put("/me", response_model=MeOut)
def update_me(payload: ProfileUpdate, user: CurrentUser, db: DbSession):
    """Partial update of the authenticated user's profile, tags and portfolio."""
    profile = user.profile
    data = payload.model_dump(exclude_unset=True)
    tags = data.pop("tags", None)
    hackathons = data.pop("hackathons", None)
    past_projects = data.pop("past_projects", None)

    if data.get("username") is None:
        data.pop("username", None)
    elif data["username"].lower() != profile.username.lower():
        taken = db.scalar(
            select(Profile.id).where(
                func.lower(Profile.username) == data["username"].lower(), Profile.id != profile.id
            )
        )
        if taken:
            raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")

    for field, value in data.items():
        setattr(profile, field, value)

    if tags is not None:
        wanted = {t["tag_id"]: t.get("level") for t in tags}  # last entry wins on duplicates
        ensure_tags_exist(db, wanted)
        existing = {link.tag_id: link for link in user.tag_links}
        for tag_id, link in existing.items():
            if tag_id not in wanted:
                user.tag_links.remove(link)
            else:
                link.level = wanted[tag_id]
        for tag_id, level in wanted.items():
            if tag_id not in existing:
                user.tag_links.append(UserTagLink(tag_id=tag_id, level=level))

    if hackathons is not None:
        profile.hackathons = [HackathonEntry(**h) for h in hackathons]
    if past_projects is not None:
        profile.past_projects = [PastProject(**p) for p in past_projects]

    db.commit()
    return user


@router.get("/browse", response_model=list[BrowseUserOut])
def browse_users(
    user: CurrentUser,
    db: DbSession,
    region: str | None = Query(default=None, max_length=100),
    q: str | None = Query(default=None, max_length=100, description="Search username or bio"),
    tag_ids: list[int] = Query(default=[], description="Only users having ANY of these tags"),
    min_overlap: int = Query(default=0, ge=0, description="Minimum shared tags"),
    for_project_id: int | None = Query(
        default=None, description="Rank by this project's tags instead of your own (owner only)"
    ),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    """The 'swipe' feed of developers, ranked by number of shared tags (best match first).

    Developers you already liked/passed are excluded. Users with no overlap are still
    returned, ranked last, unless `min_overlap` is set.
    """
    exclude: list[int] = []
    if for_project_id is not None:
        project = db.get(Project, for_project_id)
        if project is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
        if project.owner_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the project owner can do this")
        reference = matching.project_tag_ids(db, for_project_id)
        exclude = matching.project_member_ids(db, for_project_id)
    else:
        reference = matching.user_tag_ids(db, user.id)

    rows = matching.browse_users(
        db,
        user,
        reference_tag_ids=reference,
        region=region,
        q=q,
        filter_tag_ids=tag_ids,
        min_overlap=min_overlap,
        exclude_user_ids=exclude,
        limit=limit,
        offset=offset,
    )
    shared = matching.shared_tags_for_users(db, [p.user_id for p, _ in rows], reference)
    return [
        BrowseUserOut(
            profile=ProfileOut.model_validate(profile),
            match_score=score,
            shared_tags=[TagOut.model_validate(t) for t in shared[profile.user_id]],
        )
        for profile, score in rows
    ]


@router.get("/{user_id}", response_model=ProfileOut)
def read_user(user_id: int, db: DbSession, _: CurrentUser):
    """Public profile of another user (no email)."""
    target = db.get(User, user_id)
    if target is None or not target.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return target.profile
