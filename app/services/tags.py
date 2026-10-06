import re
from collections.abc import Iterable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Tag


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9+#.]+", "-", name.strip().lower()).strip("-")


def ensure_tags_exist(db: Session, tag_ids: Iterable[int]) -> None:
    wanted = set(tag_ids)
    if not wanted:
        return
    found = set(db.scalars(select(Tag.id).where(Tag.id.in_(wanted))))
    if missing := wanted - found:
        raise HTTPException(
            422,
            detail=f"Unknown tag ids: {sorted(missing)}",
        )
