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
