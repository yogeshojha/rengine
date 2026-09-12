"""Connector persistence: connections, captured request shapes and the hosts they reached."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

import shared.models._tztypes  # noqa: F401
from shared.definitions.connectors import (
    MAX_NAME,
    MAX_PENDING_ACTIONS,
    ActionKind,
    CandidateState,
    ConnectorKind,
    SourceTool,
)
from shared.models.endpoint import EndpointFilter
from shared.utils.datetime import utc_now


def _json_list():
    return Field(default_factory=list, sa_column=Column(JSON, nullable=False))


class Connector(SQLModel, table=True):
    __tablename__ = "connectors"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    kind: str = Field(default=ConnectorKind.BURP.value, max_length=16, index=True)
    name: str = Field(max_length=MAX_NAME)
    token_hash: str = Field(max_length=64, index=True, unique=True)
    token_prefix: str = Field(max_length=32)

    only_known_hosts: bool = Field(default=False)
    ingest_tools: list = _json_list()
    capture_bodies: bool = Field(default=False)
    record_hosts: bool = Field(default=True)
    include_static: bool = Field(default=False)
    scan_safe_methods_only: bool = Field(default=True)
    context_id: uuid.UUID | None = Field(default=None)
    paused: bool = Field(default=False)

    requests_seen: int = Field(default=0)
    dropped_out_of_scope: int = Field(default=0)
    candidates: int = Field(default=0)
    scans_launched: int = Field(default=0)
    last_seen_at: datetime | None = Field(default=None, index=True)
    last_client: str | None = Field(default=None, max_length=120)
    last_scan_at: datetime | None = Field(default=None)
    created_by: uuid.UUID | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ConnectorCandidate(SQLModel, table=True):
    """One request shape captured by a connector."""

    __tablename__ = "connector_candidates"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    connector_id: uuid.UUID = Field(foreign_key="connectors.id", index=True)
    project_id: uuid.UUID = Field(index=True)
    target_id: uuid.UUID | None = Field(default=None, index=True)
    signature: str = Field(max_length=64, index=True)

    url: str = Field(max_length=2000)
    scheme: str = Field(max_length=8)
    host: str = Field(max_length=500, index=True)
    port: int = Field(default=443)
    path: str = Field(max_length=1500)
    dir_path: str = Field(max_length=1500)
    filename: str | None = Field(default=None, max_length=300)
    extension: str | None = Field(default=None, max_length=16)
    depth: int = Field(default=0)

    methods: list = _json_list()
    params: list = _json_list()
    param_count: int = Field(default=0, index=True)
    endpoint_class: str | None = Field(default=None, max_length=24, index=True)
    interests: list = _json_list()
    notices: list = _json_list()

    status_code: int | None = Field(default=None, index=True)
    content_type: str | None = Field(default=None, max_length=120)
    content_length: int | None = Field(default=None)
    title: str | None = Field(default=None, max_length=500)
    authenticated: bool = Field(default=False, index=True)
    source_tool: str = Field(default=SourceTool.PROXY.value, max_length=16)
    request_sample: str | None = Field(default=None)

    known: bool = Field(default=False, index=True)
    state: str = Field(default=CandidateState.NEW.value, max_length=16, index=True)
    hits: int = Field(default=1)
    scan_id: uuid.UUID | None = Field(default=None)
    notified_at: datetime | None = Field(default=None, index=True)
    first_seen_at: datetime = Field(default_factory=utc_now, index=True)
    last_seen_at: datetime = Field(default_factory=utc_now, index=True)


class ConnectorAction(SQLModel, table=True):
    """Work queued for the proxy to collect."""

    __tablename__ = "connector_actions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    connector_id: uuid.UUID = Field(foreign_key="connectors.id", index=True)
    kind: str = Field(default=ActionKind.REPEATER.value, max_length=16)
    url: str = Field(max_length=2000)
    method: str = Field(default="GET", max_length=16)
    label: str | None = Field(default=None, max_length=120)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    delivered_at: datetime | None = Field(default=None, index=True)


class ConnectorHost(SQLModel, table=True):
    """Every hostname a connector has reached."""

    __tablename__ = "connector_hosts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    connector_id: uuid.UUID = Field(foreign_key="connectors.id", index=True)
    project_id: uuid.UUID = Field(index=True)
    host: str = Field(max_length=500, index=True)
    registrable: str = Field(default="", max_length=500, index=True)
    target_id: uuid.UUID | None = Field(default=None, index=True)
    requests: int = Field(default=0)
    dismissed: bool = Field(default=False, index=True)
    first_seen_at: datetime = Field(default_factory=utc_now)
    last_seen_at: datetime = Field(default_factory=utc_now, index=True)


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ids: list[uuid.UUID] = PydanticField(default_factory=list, max_length=200)
    kind: str = PydanticField(default=ActionKind.REPEATER.value, max_length=16)


class EndpointActionRequest(BaseModel):
    """Endpoints to hand to the proxy: chosen rows, or everything a filter names, capped."""

    model_config = ConfigDict(extra="forbid")

    endpoint_ids: list[uuid.UUID] = PydanticField(default_factory=list, max_length=200)
    filter: EndpointFilter | None = None
    limit: int = PydanticField(
        default=MAX_PENDING_ACTIONS, ge=1, le=MAX_PENDING_ACTIONS
    )
    kind: str = PydanticField(default=ActionKind.REPEATER.value, max_length=16)


class CandidateIds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ids: list[uuid.UUID] = PydanticField(default_factory=list, max_length=5000)


class CandidateStateRequest(CandidateIds):
    state: str = PydanticField(max_length=16)


class TargetOption(BaseModel):
    """Something the proxy can pick while testing: a target, or a whole program."""

    id: uuid.UUID
    value: str
    target_type: str
    kind: str = "target"
    scanned: bool = False
    endpoints: int = 0
    targets: int = 0


class NoticeRead(BaseModel):
    """A notice shown to the tester."""

    kind: str
    label: str
    url: str
    host: str
    status_code: int | None = None
    seen_at: datetime


class FindingReport(BaseModel):
    """A finding a person confirmed by hand, reported from the proxy."""

    model_config = ConfigDict(extra="forbid")

    title: str = PydanticField(min_length=1, max_length=500)
    url: str = PydanticField(min_length=1, max_length=2000)
    severity: str = PydanticField(default="medium", max_length=16)
    method: str = PydanticField(default="GET", max_length=16)
    notes: str | None = PydanticField(default=None, max_length=8000)
    request: str | None = PydanticField(default=None, max_length=200_000)
    response: str | None = PydanticField(default=None, max_length=200_000)


class FindingRecorded(BaseModel):
    finding_id: uuid.UUID
    scan_id: uuid.UUID
    target_value: str
    total: int = 0


class ConnectorScope(BaseModel):
    """Scope rules for the proxy."""

    target_value: str
    include: list[str] = PydanticField(default_factory=list)
    exclude: list[str] = PydanticField(default_factory=list)
    hosts_known: int = 0
    truncated: bool = False
    from_program: str | None = None
    from_scope_rules: bool = False


class HostFacts(BaseModel):
    """Known facts about the host under test."""

    host: str
    target_value: str | None = None
    covered: bool = False
    known_endpoints: int = 0
    visited: int = 0
    unvisited: int = 0
    flagged: int = 0
    last_scan_at: datetime | None = None


class ActionRead(BaseModel):
    kind: str
    url: str
    method: str
    label: str | None = None


class DiscoveredDomain(BaseModel):
    """A registrable domain a connector reached that no target covers."""

    domain: str
    reason: str
    reason_label: str
    reason_detail: str
    hostnames: list[str] = PydanticField(default_factory=list)
    hostname_count: int = 0
    requests: int = 0
    out_of_scope: bool = False
    program: str | None = None
    first_seen_at: datetime
    last_seen_at: datetime


class ConnectorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = PydanticField(min_length=1, max_length=MAX_NAME)
    kind: str = PydanticField(default=ConnectorKind.BURP.value, max_length=16)
    project_id: uuid.UUID
    only_known_hosts: bool = False
    ingest_tools: list[str] = PydanticField(default_factory=list, max_length=4)
    capture_bodies: bool = False
    record_hosts: bool = True
    include_static: bool = False
    scan_safe_methods_only: bool = True
    context_id: uuid.UUID | None = None


class ConnectorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = PydanticField(default=None, min_length=1, max_length=MAX_NAME)
    only_known_hosts: bool | None = None
    ingest_tools: list[str] | None = PydanticField(default=None, max_length=4)
    capture_bodies: bool | None = None
    record_hosts: bool | None = None
    include_static: bool | None = None
    scan_safe_methods_only: bool | None = None
    context_id: uuid.UUID | None = None
    paused: bool | None = None


class ConnectorRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    kind: str
    name: str
    token_prefix: str
    only_known_hosts: bool
    ingest_tools: list[str]
    capture_bodies: bool
    record_hosts: bool
    include_static: bool
    scan_safe_methods_only: bool
    context_id: uuid.UUID | None
    paused: bool
    state: str
    requests_seen: int
    dropped_out_of_scope: int
    candidates: int
    queued: int
    unseen: int
    unassigned: int
    flagged: int
    out_of_scope: int
    discovered: int
    scans_launched: int
    pending_actions: int
    last_seen_at: datetime | None
    last_client: str | None
    last_scan_at: datetime | None
    created_at: datetime


class ConnectorCreated(BaseModel):
    """The one time the secret is returned."""

    connector: ConnectorRead
    secret: str
    setup: dict


class CandidateRead(BaseModel):
    id: uuid.UUID
    target_id: uuid.UUID | None
    url: str
    host: str
    path: str
    methods: list[str]
    params: list[str]
    param_count: int
    endpoint_class: str | None
    interests: list[str]
    notices: list[str]
    status_code: int | None
    content_type: str | None
    content_length: int | None
    title: str | None
    authenticated: bool
    source_tool: str
    request_sample: str | None
    known: bool
    state: str
    hits: int
    scan_id: uuid.UUID | None
    first_seen_at: datetime
    last_seen_at: datetime


class CandidatePage(BaseModel):
    rows: list[CandidateRead]
    total: int
    counts: dict[str, int]
    hosts: list[dict]


class AddTargetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str = PydanticField(min_length=1, max_length=500)
    scan: bool = False


class TargetAdded(BaseModel):
    target_id: uuid.UUID
    target_value: str
    attached: int = 0
    scan_id: uuid.UUID | None = None


class IngestItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = PydanticField(max_length=2000)
    method: str = PydanticField(default="GET", max_length=16)
    status_code: int | None = None
    content_type: str | None = PydanticField(default=None, max_length=120)
    content_length: int | None = None
    title: str | None = PydanticField(default=None, max_length=500)
    authenticated: bool = False
    source_tool: str = PydanticField(default=SourceTool.PROXY.value, max_length=16)
    body_params: list[str] = PydanticField(default_factory=list, max_length=40)
    request_sample: str | None = PydanticField(default=None, max_length=4000)
    observed_at: datetime | None = None


class IngestRequest(BaseModel):
    """One batch from a proxy."""

    model_config = ConfigDict(extra="forbid")

    client: str | None = PydanticField(default=None, max_length=120)
    target_id: uuid.UUID | None = None
    program_id: uuid.UUID | None = None
    items: list[IngestItem] = PydanticField(default_factory=list, max_length=500)


class IngestResult(BaseModel):
    accepted: int
    novel: int
    dropped: int
    queued: int
    recorded: int = 0
    flagged: list[dict]
