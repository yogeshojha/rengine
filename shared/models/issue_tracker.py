import uuid
from datetime import datetime
from functools import partial

from pydantic import BaseModel, field_validator
from pydantic import Field as PydanticField
from sqlalchemy import Column, Index, Text, UniqueConstraint, text
from sqlmodel import Field, SQLModel

from shared.definitions.issue_trackers import (
    MAX_DESTINATION,
    MAX_ERROR,
    MAX_FILE_CHECKS,
    MAX_FILE_SELECTION,
    MAX_ISSUE_TYPE,
    MAX_KEY,
    MAX_NAME,
    MAX_REMOTE_STATUS,
    MAX_TITLE,
    MAX_URL,
    CommentState,
    FilingState,
    Grouping,
)
from shared.utils.datetime import utc_now
from shared.utils.validation import clean_name, clean_optional_name


class IssueTracker(SQLModel, table=True):
    __tablename__ = "issue_trackers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=MAX_NAME)
    kind: str = Field(max_length=20)
    url: str = Field(max_length=MAX_URL)
    config_encrypted: str = Field(default="")
    destination: str | None = Field(default=None, max_length=MAX_DESTINATION)
    issue_type: str | None = Field(default=None, max_length=MAX_ISSUE_TYPE)
    is_active: bool = Field(default=True)
    created_by: uuid.UUID | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_test_at: datetime | None = Field(default=None)
    last_test_ok: bool | None = Field(default=None)
    last_test_message: str | None = Field(default=None, max_length=MAX_ERROR)


class IssueTrackerRoute(SQLModel, table=True):
    __tablename__ = "issue_tracker_routes"
    __table_args__ = (
        Index(
            "uq_issue_route_project",
            "project_id",
            unique=True,
            postgresql_where=text("target_id IS NULL"),
        ),
        Index(
            "uq_issue_route_target",
            "project_id",
            "target_id",
            unique=True,
            postgresql_where=text("target_id IS NOT NULL"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(
        foreign_key="projects.id", index=True, ondelete="CASCADE"
    )
    target_id: uuid.UUID | None = Field(
        default=None, foreign_key="targets.id", ondelete="CASCADE"
    )
    tracker_id: uuid.UUID = Field(
        foreign_key="issue_trackers.id", index=True, ondelete="CASCADE"
    )
    destination: str = Field(max_length=MAX_DESTINATION)
    issue_type: str | None = Field(default=None, max_length=MAX_ISSUE_TYPE)
    created_at: datetime = Field(default_factory=utc_now)


class TrackedIssue(SQLModel, table=True):
    __tablename__ = "tracked_issues"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tracker_id: uuid.UUID = Field(
        foreign_key="issue_trackers.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(
        foreign_key="projects.id", index=True, ondelete="CASCADE"
    )
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    template_id: str = Field(max_length=200)
    severity: str = Field(max_length=16)
    grouped: bool = Field(default=False)
    destination: str = Field(max_length=MAX_DESTINATION)
    issue_type: str | None = Field(default=None, max_length=MAX_ISSUE_TYPE)
    title: str = Field(max_length=MAX_TITLE)
    state: str = Field(default=FilingState.PENDING.value, max_length=16, index=True)
    external_key: str | None = Field(default=None, max_length=MAX_KEY)
    external_id: str | None = Field(default=None, max_length=MAX_KEY)
    url: str | None = Field(default=None, max_length=1000)
    remote_status: str | None = Field(default=None, max_length=MAX_REMOTE_STATUS)
    remote_category: str | None = Field(default=None, max_length=16)
    done_noted: bool = Field(default=False)
    error: str | None = Field(default=None, max_length=MAX_ERROR)
    attempts: int = Field(default=0)
    created_by: uuid.UUID | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    filed_at: datetime | None = Field(default=None)
    status_read_at: datetime | None = Field(default=None)


class TrackedIssueFinding(SQLModel, table=True):
    __tablename__ = "tracked_issue_findings"
    __table_args__ = (
        UniqueConstraint(
            "tracker_id", "target_id", "fingerprint", name="uq_tracked_finding"
        ),
        Index("ix_tracked_finding_target_fp", "target_id", "fingerprint"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    issue_id: uuid.UUID = Field(
        foreign_key="tracked_issues.id", index=True, ondelete="CASCADE"
    )
    tracker_id: uuid.UUID = Field(foreign_key="issue_trackers.id", ondelete="CASCADE")
    target_id: uuid.UUID = Field(foreign_key="targets.id", ondelete="CASCADE")
    fingerprint: str = Field(max_length=64)
    matched_at: str = Field(max_length=2000)
    severity: str = Field(max_length=16)
    present: bool = Field(default=True)
    announced: bool = Field(default=False)
    added_at: datetime = Field(default_factory=utc_now)


class TrackedIssueComment(SQLModel, table=True):
    __tablename__ = "tracked_issue_comments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    issue_id: uuid.UUID = Field(
        foreign_key="tracked_issues.id", index=True, ondelete="CASCADE"
    )
    kind: str = Field(max_length=24)
    body: str = Field(sa_column=Column(Text, nullable=False))
    state: str = Field(default=CommentState.PENDING.value, max_length=16, index=True)
    scan_id: uuid.UUID | None = Field(default=None)
    attempts: int = Field(default=0)
    error: str | None = Field(default=None, max_length=MAX_ERROR)
    created_at: datetime = Field(default_factory=utc_now)
    sent_at: datetime | None = Field(default=None)


# ---------- trackers ----------


class IssueTrackerCreate(BaseModel):
    name: str
    kind: str
    url: str | None = PydanticField(default=None, max_length=MAX_URL)
    config: dict
    destination: str | None = PydanticField(default=None, max_length=MAX_DESTINATION)
    issue_type: str | None = PydanticField(default=None, max_length=MAX_ISSUE_TYPE)
    is_active: bool = True

    _validate_name = field_validator("name")(clean_name)


class IssueTrackerUpdate(BaseModel):
    name: str | None = None
    url: str | None = PydanticField(default=None, max_length=MAX_URL)
    config: dict | None = None
    destination: str | None = PydanticField(default=None, max_length=MAX_DESTINATION)
    issue_type: str | None = PydanticField(default=None, max_length=MAX_ISSUE_TYPE)
    is_active: bool | None = None

    _validate_name = field_validator("name")(
        partial(clean_optional_name, max_len=MAX_NAME)
    )


class IssueTrackerRead(BaseModel):
    id: uuid.UUID
    name: str
    kind: str
    url: str
    config_masked: dict
    destination: str | None
    issue_type: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_test_at: datetime | None
    last_test_ok: bool | None
    last_test_message: str | None
    issues_filed: int = 0
    issues_failed: int = 0


class IssueTrackerTestConfig(BaseModel):
    kind: str
    url: str | None = PydanticField(default=None, max_length=MAX_URL)
    config: dict
    tracker_id: uuid.UUID | None = None


class IssueTrackerTestResult(BaseModel):
    success: bool
    message: str


class TrackerOption(BaseModel):
    key: str
    name: str


class RouteRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    target_id: uuid.UUID | None
    target_value: str | None = None
    tracker_id: uuid.UUID
    destination: str
    issue_type: str | None


class RouteSet(BaseModel):
    project_id: uuid.UUID
    target_id: uuid.UUID | None = None
    tracker_id: uuid.UUID
    destination: str = PydanticField(min_length=1, max_length=MAX_DESTINATION)
    issue_type: str | None = PydanticField(default=None, max_length=MAX_ISSUE_TYPE)


# ---------- filing ----------


class FileSelection(BaseModel):
    fingerprints: list[str] = PydanticField(
        default_factory=list, max_length=MAX_FILE_SELECTION
    )
    template_ids: list[str] = PydanticField(
        default_factory=list, max_length=MAX_FILE_CHECKS
    )
    tracker_id: uuid.UUID | None = None
    destination: str | None = PydanticField(default=None, max_length=MAX_DESTINATION)
    issue_type: str | None = PydanticField(default=None, max_length=MAX_ISSUE_TYPE)
    grouping: Grouping = Grouping.AUTO
    title: str | None = PydanticField(default=None, max_length=MAX_TITLE)


class PreviewBlock(BaseModel):
    kind: str
    text: str = ""
    items: list[list[str]] = PydanticField(default_factory=list)
    lines: list[str] = PydanticField(default_factory=list)
    href: str = ""
    lang: str = ""


class PlannedIssue(BaseModel):
    tracker_name: str
    destination: str
    title: str
    severity: str
    grouped: bool
    findings: int
    target_value: str
    attach_to: str | None = None


class FilingPlan(BaseModel):
    tracker_id: uuid.UUID | None
    tracker_name: str | None
    tracker_kind: str | None = None
    destination: str | None
    issue_type: str | None
    grouping: str
    issues: list[PlannedIssue] = PydanticField(default_factory=list)
    new_issues: int = 0
    attached: int = 0
    already_filed: int = 0
    not_filed: int = 0
    findings: int = 0
    preview: list[PreviewBlock] | None = None
    refusal: str | None = None


class TrackedIssueRead(BaseModel):
    id: uuid.UUID
    tracker_id: uuid.UUID
    tracker_name: str
    tracker_kind: str
    target_id: uuid.UUID
    target_value: str | None = None
    template_id: str
    severity: str
    grouped: bool
    destination: str
    title: str
    state: str
    external_key: str | None
    url: str | None
    remote_status: str | None
    remote_category: str | None
    error: str | None
    findings: int = 0
    present: int = 0
    created_at: datetime
    filed_at: datetime | None
    status_read_at: datetime | None


class FilingResult(BaseModel):
    new_issues: int = 0
    attached: int = 0
    already_filed: int = 0
    not_filed: int = 0
    issues: list[TrackedIssueRead] = PydanticField(default_factory=list)


class TicketRef(BaseModel):
    issue_id: uuid.UUID
    tracker_name: str
    tracker_kind: str
    state: str
    external_key: str | None = None
    url: str | None = None
    remote_status: str | None = None
    remote_category: str | None = None
    error: str | None = None
