"""One CVE across both findings dimensions, counted on the evidence ladder."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class CveLadderStep(BaseModel):
    evidence: str
    label: str
    help: str
    count: int = 0
    software: int = 0
    findings: int = 0


class CveLocation(BaseModel):
    dimension: str
    id: uuid.UUID
    scan_id: uuid.UUID
    target_id: uuid.UUID
    target_value: str | None = None
    host: str | None = None
    ip: str | None = None
    port: int | None = None
    url: str | None = None
    evidence: str
    evidence_label: str
    basis: str
    detail: str | None = None
    severity: str
    state: str | None = None
    confidence: str | None = None
    caveats: list[str] = Field(default_factory=list)
    discovered_at: datetime


class CveTargetRow(BaseModel):
    target_id: uuid.UUID
    target_value: str
    target_type: str
    assets: int = 0
    software: int = 0
    findings: int = 0
    first_seen: datetime | None = None


class CveExposure(BaseModel):
    cve: str
    known: bool = False
    severity: str | None = None
    cvss_score: float | None = None
    cvss_vector: str | None = None
    description: str | None = None
    published_at: datetime | None = None
    last_modified_at: datetime | None = None
    epss_score: float | None = None
    epss_percentile: float | None = None
    band: str | None = None
    is_kev: bool = False
    kev_ransomware: bool = False
    kev_date_added: date | None = None
    kev_due_date: date | None = None
    kev_required_action: str | None = None
    exploit_score: int = 0
    intel_kinds: list[str] = Field(default_factory=list)
    assets: int = 0
    targets: int = 0
    software_rows: int = 0
    finding_rows: int = 0
    suppressed: int = 0
    ladder: list[CveLadderStep] = Field(default_factory=list)
    first_seen: datetime | None = None
    software_scans: int = 0
    finding_scans: int = 0
    corpus_ready: bool = False
    by_target: list[CveTargetRow] = Field(default_factory=list)
    locations: list[CveLocation] = Field(default_factory=list)
    locations_total: int = 0
    generated_at: datetime


class CveIndexRow(BaseModel):
    cve: str
    severity: str | None = None
    cvss_score: float | None = None
    epss_score: float | None = None
    is_kev: bool = False
    kev_ransomware: bool = False
    exploit_score: int = 0
    assets: int = 0
    targets: int = 0
    software: int = 0
    findings: int = 0
    top_evidence: str
    first_seen: datetime | None = None


class CveIndex(BaseModel):
    items: list[CveIndexRow] = Field(default_factory=list)
    total: int = 0
    matched: int = 0
    page: int = 1
    size: int = 50
    severity_counts: dict[str, int] = Field(default_factory=dict)
    software_scans: int = 0
    finding_scans: int = 0
    corpus_ready: bool = False
    generated_at: datetime
