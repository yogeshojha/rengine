from pydantic import BaseModel, Field


class FlowNode(BaseModel):
    id: str
    label: str
    count: int
    column: int
    tone: str
    query: str | None = None
    detail: str | None = None


class FlowLink(BaseModel):
    source: str
    target: str
    count: int
    query: str | None = None


class HostingFlow(BaseModel):
    hosts: int = 0
    resolving: int = 0
    networks: int = 0
    nodes: list[FlowNode] = Field(default_factory=list)
    links: list[FlowLink] = Field(default_factory=list)
