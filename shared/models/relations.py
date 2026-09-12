import uuid

from pydantic import BaseModel, Field


class RelationEvidence(BaseModel):
    kind: str
    label: str
    value: str
    detail: str = ""


class RelatedTarget(BaseModel):
    target_id: uuid.UUID
    target_value: str
    reasons: list[RelationEvidence] = Field(default_factory=list)


class TargetRelations(BaseModel):
    items: list[RelatedTarget] = Field(default_factory=list)
    total: int = 0
    considered: int = 0


class ProgramMatch(BaseModel):
    program_id: uuid.UUID
    handle: str
    name: str
    platform: str
    url: str | None = None
    scope_identifier: str = ""
    asset_type: str = ""
    wildcard: bool = False
    in_scope: bool = True
    offers_bounties: bool = False
    eligible_for_bounty: bool | None = None
    max_severity: str | None = None


class TargetPrograms(BaseModel):
    items: list[ProgramMatch] = Field(default_factory=list)
    total: int = 0
