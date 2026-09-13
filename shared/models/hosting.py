from pydantic import BaseModel, Field


class HostingSlice(BaseModel):
    kind: str
    label: str
    count: int
    query: str | None = None


class HostingNetwork(BaseModel):
    id: str
    label: str
    detail: str | None = None
    count: int
    query: str | None = None
    fronting: list[HostingSlice] = Field(default_factory=list)


class HostingComposition(BaseModel):
    hosts: int = 0
    resolving: int = 0
    attributed: int = 0
    networks: int = 0
    fronting: list[HostingSlice] = Field(default_factory=list)
    by_network: list[HostingNetwork] = Field(default_factory=list)
