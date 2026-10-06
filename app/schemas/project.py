from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.enums import ProjectStatus
from app.schemas.common import ORMModel, UserBrief
from app.schemas.tag import TagOut


class RoleIn(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    slots: int = Field(default=1, ge=1, le=50)


class RoleOut(ORMModel, RoleIn):
    id: int


class ProjectCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    region: str | None = Field(default=None, max_length=100)
    hackathon_name: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    deadline: date | None = None
    tag_ids: list[int] = []
    roles: list[RoleIn] = []

    @model_validator(mode="after")
    def _dates_in_order(self) -> Self:
        if self.start_date and self.deadline and self.deadline < self.start_date:
            raise ValueError("deadline must not be before start_date")
        return self


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    region: str | None = Field(default=None, max_length=100)
    hackathon_name: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    deadline: date | None = None
    status: ProjectStatus | None = None
    tag_ids: list[int] | None = None


class ProjectSummaryOut(ORMModel):
    id: int
    title: str
    description: str
    status: ProjectStatus
    region: str | None
    hackathon_name: str | None
    start_date: date | None
    deadline: date | None
    created_at: datetime
    owner: UserBrief
    tags: list[TagOut]
    roles: list[RoleOut]


class MemberOut(ORMModel):
    user_id: int
    username: str | None
    role: RoleOut | None
    joined_at: datetime


class ProjectDetailOut(ProjectSummaryOut):
    members: list[MemberOut]


class BrowseProjectOut(BaseModel):
    project: ProjectSummaryOut
    match_score: int
    shared_tags: list[TagOut]
