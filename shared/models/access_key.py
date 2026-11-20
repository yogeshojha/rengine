import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic import Field as PydanticField
from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

import shared.models._tztypes  # noqa: F401
from shared.definitions.access_keys import (
    DEFAULT_EXPIRY_DAYS,
    EXPIRY_DAYS,
    EXPIRY_DETAIL,
    MAX_NAME_LENGTH,
    AccessKeyLevel,
)
from shared.utils.datetime import utc_now

LEVEL_TYPE = SAEnum(
    AccessKeyLevel,
    name="accesskeylevel",
    values_callable=lambda levels: [level.value for level in levels],
)


class AccessKey(SQLModel, table=True):
    __tablename__ = "access_keys"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    name: str = Field(max_length=MAX_NAME_LENGTH)
    prefix: str = Field(max_length=32)
    token_hash: str = Field(max_length=64, unique=True, index=True)
    access: AccessKeyLevel = Field(sa_column=Column(LEVEL_TYPE, nullable=False))
    expires_at: datetime | None = Field(default=None)
    revoked_at: datetime | None = Field(default=None)
    last_used_at: datetime | None = Field(default=None)
    last_used_ip: str | None = Field(default=None, max_length=64)
    use_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=utc_now)


class AccessKeyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = PydanticField(min_length=1, max_length=MAX_NAME_LENGTH)
    access: AccessKeyLevel = AccessKeyLevel.READ
    expires_in_days: int | None = DEFAULT_EXPIRY_DAYS

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            message = "Enter a name."
            raise ValueError(message)
        return value

    @field_validator("expires_in_days")
    @classmethod
    def _expiry(cls, value: int | None) -> int | None:
        if value not in EXPIRY_DAYS:
            raise ValueError(EXPIRY_DETAIL)
        return value


class AccessKeyRead(BaseModel):
    id: uuid.UUID
    name: str
    prefix: str
    access: AccessKeyLevel
    expires_at: datetime | None
    expired: bool
    last_used_at: datetime | None
    last_used_ip: str | None
    use_count: int
    created_at: datetime


class AccessKeyCreated(AccessKeyRead):
    key: str
    first_request: str
