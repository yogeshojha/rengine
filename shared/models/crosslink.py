import uuid

from pydantic import BaseModel, Field


class CrossLinkPeer(BaseModel):
    host: str
    target_id: uuid.UUID | None = None
    target_value: str = ""


class CrossLink(BaseModel):
    kind: str
    label: str
    value: str
    query: str
    peers: list[CrossLinkPeer] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)
    hosts: int = 0
