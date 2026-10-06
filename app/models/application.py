from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import ApplicationStatus, RewardType
from app.models.common import enum_col, utcnow
from app.models.project import Project, ProjectRole
from app.models.user import User


class Application(Base):
    """The formal join request: availability, timezone, abilities, pitch and reward terms."""

    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("project_id", "applicant_id", name="uq_application_once"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    applicant_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role_id: Mapped[int | None] = mapped_column(ForeignKey("project_roles.id", ondelete="SET NULL"))

    hours_per_week: Mapped[int]
    timezone: Mapped[str] = mapped_column(String(64))
    abilities: Mapped[str] = mapped_column(Text)  # skills offered for *this* project
    value_pitch: Mapped[str] = mapped_column(Text)

    # Reward terms. Only FLAT_FEE is payable and therefore goes through /payments.
    reward_type: Mapped[RewardType] = mapped_column(enum_col(RewardType))
    reward_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    reward_details: Mapped[str | None] = mapped_column(Text)  # e.g. "2% equity, 4yr vest"

    status: Mapped[ApplicationStatus] = mapped_column(
        enum_col(ApplicationStatus), default=ApplicationStatus.PENDING, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project] = relationship()
    applicant: Mapped[User] = relationship()
    role: Mapped[ProjectRole | None] = relationship()

    @property
    def is_payable(self) -> bool:
        return self.reward_type == RewardType.FLAT_FEE
