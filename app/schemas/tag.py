from pydantic import BaseModel, Field

from app.enums import SkillLevel, TagCategory
from app.schemas.common import ORMModel


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    category: TagCategory


class TagOut(ORMModel):
    id: int
    name: str
    slug: str
    category: TagCategory


class UserTagIn(BaseModel):
    tag_id: int
    level: SkillLevel | None = None


class UserTagOut(ORMModel):
    tag: TagOut
    level: SkillLevel | None = None
