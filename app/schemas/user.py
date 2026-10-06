from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel, Timezone
from app.schemas.tag import TagOut, UserTagIn, UserTagOut


class HackathonIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    year: int | None = Field(default=None, ge=1990, le=2100)
    award: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class HackathonOut(ORMModel, HackathonIn):
    id: int


class PastProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    url: str | None = Field(default=None, max_length=500)


class PastProjectOut(ORMModel, PastProjectIn):
    id: int


class ProfileUpdate(BaseModel):
    """Partial update: only fields that are sent are changed. Sending a list
    (tags / hackathons / past_projects) replaces the whole list; send [] to clear it."""

    username: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_]{3,30}$")
    bio: str | None = Field(default=None, max_length=2000)
    region: str | None = Field(default=None, max_length=100)
    timezone: Timezone | None = None
    interests: str | None = Field(default=None, max_length=1000)
    future_goals: str | None = Field(default=None, max_length=2000)
    tags: list[UserTagIn] | None = None
    hackathons: list[HackathonIn] | None = None
    past_projects: list[PastProjectIn] | None = None


class ProfileOut(ORMModel):
    user_id: int
    username: str
    bio: str | None
    region: str | None
    timezone: str | None
    interests: str | None
    future_goals: str | None
    tags: list[UserTagOut] = Field(validation_alias="tag_links")
    hackathons: list[HackathonOut]
    past_projects: list[PastProjectOut]


class MeOut(ORMModel):
    id: int
    email: EmailStr
    stripe_connected: bool = False
    profile: ProfileOut


class BrowseUserOut(BaseModel):
    profile: ProfileOut
    match_score: int
    shared_tags: list[TagOut]
