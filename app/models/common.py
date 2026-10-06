import enum
from datetime import datetime, timezone

from sqlalchemy import Enum


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def enum_col(enum_cls: type[enum.Enum], length: int = 32) -> Enum:
    """Store enums as plain VARCHAR holding the member *value* (no native PG enum types).

    Plain strings keep migrations simple: adding a new member never needs ALTER TYPE.
    """
    return Enum(
        enum_cls,
        native_enum=False,
        create_constraint=False,
        length=length,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )
