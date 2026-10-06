from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import PaymentStatus
from app.models.application import Application
from app.models.common import enum_col, utcnow


class PaymentContract(Base):
    """Escrow record. Funds are charged at acceptance and held by the platform, then
    transferred to the developer's Stripe Connect account when the milestone is approved."""

    __tablename__ = "payment_contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="RESTRICT"), index=True
    )
    milestone_id: Mapped[int | None] = mapped_column(
        ForeignKey("milestones.id", ondelete="SET NULL")
    )
    payer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    payee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[PaymentStatus] = mapped_column(
        enum_col(PaymentStatus), default=PaymentStatus.PENDING, index=True
    )

    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    stripe_transfer_id: Mapped[str | None] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    application: Mapped[Application] = relationship()
