from functools import lru_cache
from typing import Annotated
from zoneinfo import available_timezones

from pydantic import AfterValidator, BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


@lru_cache
def _timezones() -> frozenset[str]:
    return frozenset(available_timezones())


def _check_timezone(value: str) -> str:
    if value not in _timezones():
        raise ValueError("must be a valid IANA timezone name, e.g. 'America/Mexico_City'")
    return value


# An IANA timezone name such as "Europe/Madrid" or "UTC".
Timezone = Annotated[str, AfterValidator(_check_timezone)]


class UserBrief(ORMModel):
    id: int
    username: str | None
