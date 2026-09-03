from pydantic import BaseModel, Field


class RelatedEvidence(BaseModel):
    hostname: str
    seen_on: str


class RelatedDomain(BaseModel):
    domain: str
    reason: str
    reason_label: str
    reason_detail: str
    hostnames: list[str] = Field(default_factory=list)
    hostname_count: int = 0
    evidence: list[RelatedEvidence] = Field(default_factory=list)
    is_target: bool = False


class RelatedDomains(BaseModel):
    domains: list[RelatedDomain] = Field(default_factory=list)
    root: str = ""
