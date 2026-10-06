from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import SkillLevel
from app.models.common import enum_col, utcnow
from app.models.tag import Tag


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    # Stripe Connect account that receives payouts when this user is paid for a project.
    stripe_account_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    profile: Mapped["Profile"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    tag_links: Mapped[list["UserTagLink"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def username(self) -> str | None:
        return self.profile.username if self.profile else None

    @property
    def stripe_connected(self) -> bool:
        return bool(self.stripe_account_id)


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    username: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    bio: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(String(100), index=True)
    timezone: Mapped[str | None] = mapped_column(String(64))  # IANA name, e.g. "America/Mexico_City"
    interests: Mapped[str | None] = mapped_column(Text)
    future_goals: Mapped[str | None] = mapped_column(Text)  # wishlist: hackathons / project types
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    user: Mapped[User] = relationship(back_populates="profile")
    hackathons: Mapped[list["HackathonEntry"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", order_by="HackathonEntry.year.desc()"
    )
    past_projects: Mapped[list["PastProject"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )

    @property
    def tag_links(self) -> list["UserTagLink"]:
        return self.user.tag_links


class HackathonEntry(Base):
    """Track record: one row per hackathon the user took part in."""

    __tablename__ = "hackathon_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    year: Mapped[int | None]
    award: Mapped[str | None] = mapped_column(String(200))  # e.g. "Best Beginner Hack"
    description: Mapped[str | None] = mapped_column(Text)

    profile: Mapped[Profile] = relationship(back_populates="hackathons")


class PastProject(Base):
    __tablename__ = "past_projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(500))

    profile: Mapped[Profile] = relationship(back_populates="past_projects")


class UserTagLink(Base):
    __tablename__ = "user_tag_links"
    __table_args__ = (Index("ix_user_tag_links_tag_id", "tag_id"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    # Optional per-skill proficiency (e.g. React: advanced).
    level: Mapped[SkillLevel | None] = mapped_column(enum_col(SkillLevel))

    user: Mapped[User] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship(lazy="joined")
