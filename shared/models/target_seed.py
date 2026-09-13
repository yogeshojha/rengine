import uuid
from datetime import datetime

from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.definitions.rescan import MAX_RUN_ASSETS, SeedKind
from shared.utils.datetime import utc_now

MAX_SEED_VALUE_LEN = 2000


class TargetSeed(SQLModel, table=True):
    __tablename__ = "target_seeds"
    __table_args__ = (
        UniqueConstraint("target_id", "value", name="uq_target_seed_value"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    kind: str = Field(default=SeedKind.HOST.value, max_length=16)
    value: str = Field(max_length=MAX_SEED_VALUE_LEN)
    created_at: datetime = Field(default_factory=utc_now)


class TargetSeedRead(BaseModel):
    id: uuid.UUID
    kind: str
    value: str
    created_at: datetime


class TargetSeedWrite(BaseModel):
    """Seed lines as typed or pasted. Each line is classified against the target."""

    values: list[str] = PydanticField(default_factory=list, max_length=MAX_RUN_ASSETS)
    replace: bool = False


class TargetSeedRejection(BaseModel):
    value: str
    reason: str


class TargetSeedResult(BaseModel):
    total: int
    added: int
    removed: int
    rejected: list[TargetSeedRejection] = PydanticField(default_factory=list)
