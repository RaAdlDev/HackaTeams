from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel, Field, model_validator

from app.enums import NotificationType, PostType, SwipeAction
from app.schemas.common import ORMModel, UserBrief


class SwipeCreate(BaseModel):
    target_user_id: int | None = None
    target_project_id: int | None = None
    action: SwipeAction

    @model_validator(mode="after")
    def _exactly_one_target(self) -> Self:
        if (self.target_user_id is None) == (self.target_project_id is None):
            raise ValueError("provide exactly one of target_user_id or target_project_id")
        return self


class SwipeOut(BaseModel):
    action: SwipeAction
    matched: bool


class NotificationOut(ORMModel):
    id: int
    type: NotificationType
    payload: dict[str, Any]
    is_read: bool
    created_at: datetime


class PostCreate(BaseModel):
    type: PostType
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10, max_length=3000)
    project_id: int | None = None


class PostOut(ORMModel):
    id: int
    type: PostType
    title: str
    body: str
    project_id: int | None
    author: UserBrief
    created_at: datetime
