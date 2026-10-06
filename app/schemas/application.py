from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.enums import ApplicationStatus, RewardType
from app.schemas.common import ORMModel, Timezone, UserBrief


class ApplicationCreate(BaseModel):
    """Every field except role_id and reward_details is mandatory."""

    role_id: int | None = None
    hours_per_week: int = Field(ge=1, le=168)
    timezone: Timezone
    abilities: str = Field(min_length=2, max_length=1000)
    value_pitch: str = Field(min_length=20, max_length=3000)
    reward_type: RewardType
    reward_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    reward_details: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _reward_consistent(self) -> Self:
        # Money must be declared up front so it can be settled on-platform.
        if self.reward_type == RewardType.FLAT_FEE:
            if self.reward_amount is None:
                raise ValueError("reward_amount is required when reward_type is 'flat_fee'")
        elif self.reward_amount is not None:
            raise ValueError(
                "reward_amount is only allowed for 'flat_fee'; describe equity, "
                "rev-share or learning terms in reward_details"
            )
        return self


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus

    @field_validator("status")
    @classmethod
    def _owner_decisions_only(cls, v: ApplicationStatus) -> ApplicationStatus:
        if v not in (ApplicationStatus.ACCEPTED, ApplicationStatus.REJECTED):
            raise ValueError("status must be 'accepted' or 'rejected'")
        return v


class ApplicationOut(ORMModel):
    id: int
    project_id: int
    applicant: UserBrief
    role_id: int | None
    hours_per_week: int
    timezone: str
    abilities: str
    value_pitch: str
    reward_type: RewardType
    reward_amount: Decimal | None
    currency: str
    reward_details: str | None
    is_payable: bool
    status: ApplicationStatus
    created_at: datetime
    decided_at: datetime | None
