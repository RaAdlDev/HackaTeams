from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.enums import TagCategory
from app.models.common import enum_col, utcnow


class Tag(Base):
    """Abilities, objectives and expertise levels. `slug` is the normalized identity,
    so "React", "react" and " REACT " are the same tag."""

    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("category", "slug", name="uq_tag_category_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    slug: Mapped[str] = mapped_column(String(60), index=True)
    category: Mapped[TagCategory] = mapped_column(enum_col(TagCategory), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
