from fastapi import APIRouter, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import CurrentUser, DbSession
from app.enums import TagCategory
from app.models import Tag
from app.schemas.tag import TagCreate, TagOut
from app.services.tags import slugify

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagOut])
def list_tags(
    db: DbSession,
    category: TagCategory | None = None,
    q: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(Tag).order_by(Tag.category, Tag.name).limit(limit).offset(offset)
    if category:
        stmt = stmt.where(Tag.category == category)
    if q:
        stmt = stmt.where(Tag.name.icontains(q, autoescape=True))
    return db.scalars(stmt).all()


@router.post("", response_model=TagOut, status_code=status.HTTP_201_CREATED)
def create_tag(payload: TagCreate, db: DbSession, _: CurrentUser):
    """Get-or-create. Names are normalized, so 'React' and 'react' resolve to one tag."""
    slug = slugify(payload.name)
    existing = db.scalar(select(Tag).where(Tag.category == payload.category, Tag.slug == slug))
    if existing:
        return existing
    tag = Tag(name=payload.name.strip(), slug=slug, category=payload.category)
    db.add(tag)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return db.scalar(select(Tag).where(Tag.category == payload.category, Tag.slug == slug))
    return tag
