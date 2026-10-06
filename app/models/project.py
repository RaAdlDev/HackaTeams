from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import MilestoneStatus, ProjectStatus
from app.models.common import enum_col, utcnow
from app.models.tag import Tag
from app.models.user import User


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[ProjectStatus] = mapped_column(
        enum_col(ProjectStatus), default=ProjectStatus.OPEN, index=True
    )
    region: Mapped[str | None] = mapped_column(String(100), index=True)
    hackathon_name: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[date | None] = mapped_column(Date)
    deadline: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    owner: Mapped[User] = relationship()
    tag_links: Mapped[list["ProjectTagLink"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    roles: Mapped[list["ProjectRole"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ProjectRole.id"
    )
    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ProjectMember.id"
    )
    milestones: Mapped[list["Milestone"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Milestone.id"
    )

    @property
    def tags(self) -> list[Tag]:
        return [link.tag for link in self.tag_links]


class ProjectTagLink(Base):
    __tablename__ = "project_tag_links"
    __table_args__ = (Index("ix_project_tag_links_tag_id", "tag_id"),)

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    project: Mapped[Project] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship(lazy="joined")


class ProjectRole(Base):
    """A position the project is recruiting for (e.g. "Backend dev", slots=2)."""

    __tablename__ = "project_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    slots: Mapped[int] = mapped_column(default=1)

    project: Mapped[Project] = relationship(back_populates="roles")


class ProjectMember(Base):
    """Created when an application is accepted. The owner is not a member row."""

    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role_id: Mapped[int | None] = mapped_column(ForeignKey("project_roles.id", ondelete="SET NULL"))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped[Project] = relationship(back_populates="members")
    user: Mapped[User] = relationship()
    role: Mapped[ProjectRole | None] = relationship()

    @property
    def username(self) -> str | None:
        return self.user.username


class Milestone(Base):
    """Deliverable that gates a payment release (used by the payments phase)."""

    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[MilestoneStatus] = mapped_column(
        enum_col(MilestoneStatus), default=MilestoneStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped[Project] = relationship(back_populates="milestones")
