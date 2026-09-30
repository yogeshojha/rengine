"""Issue tracker vocabulary: kinds, fields, filing states, remote status and grouping."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from shared.definitions.evidence import Evidence
from shared.definitions.vulnerabilities import Severity

MAX_NAME = 120
MAX_URL = 500
MAX_DESTINATION = 200
MAX_ISSUE_TYPE = 100
MAX_KEY = 250
MAX_TITLE = 255
MAX_ERROR = 500
MAX_REMOTE_STATUS = 100
MAX_TRACKERS = 20
MAX_FILE_SELECTION = 500
MAX_FILE_CHECKS = 100
MAX_LISTED = 500
MAX_GROUP_LOCATIONS = 50
MAX_EVIDENCE_CHARS = 4000
STATUS_BATCH = 100
STATUS_REFRESH_SECONDS = 1800
PENDING_GRACE_SECONDS = 300
MAX_COMMENT_ATTEMPTS = 3
SHEET_REFRESH_SECONDS = 300
DESTINATION_LIMIT = 50
TRACKER_LABEL = "rengine"


class TrackerKind(StrEnum):
    JIRA_CLOUD = "jira_cloud"
    JIRA_DC = "jira_dc"
    GITHUB = "github"
    GITLAB = "gitlab"


class TrackerFamily(StrEnum):
    JIRA = "jira"
    GITHUB = "github"
    GITLAB = "gitlab"


class BodyFormat(StrEnum):
    ADF = "adf"
    WIKI = "wiki"
    MARKDOWN = "markdown"


@dataclass(frozen=True)
class TrackerField:
    key: str
    label: str
    secret: bool = False
    placeholder: str = ""
    help: str = ""


@dataclass(frozen=True)
class TrackerSpec:
    kind: TrackerKind
    label: str
    family: TrackerFamily
    body_format: BodyFormat
    url_label: str
    url_placeholder: str
    default_url: str | None
    destination_label: str
    destination_placeholder: str
    has_issue_type: bool
    fields: tuple[TrackerField, ...]
    docs_url: str
    body_limit: int
    create_interval: float


TRACKERS: tuple[TrackerSpec, ...] = (
    TrackerSpec(
        kind=TrackerKind.JIRA_CLOUD,
        label="Jira Cloud",
        family=TrackerFamily.JIRA,
        body_format=BodyFormat.ADF,
        url_label="Site URL",
        url_placeholder="https://acme.atlassian.net",
        default_url=None,
        destination_label="Project",
        destination_placeholder="SEC",
        has_issue_type=True,
        fields=(
            TrackerField(key="email", label="Account email"),
            TrackerField(
                key="token",
                label="API token",
                secret=True,
                help="id.atlassian.com > Security > API tokens.",
            ),
        ),
        docs_url="https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/",
        body_limit=32_000,
        create_interval=0.3,
    ),
    TrackerSpec(
        kind=TrackerKind.JIRA_DC,
        label="Jira Data Center",
        family=TrackerFamily.JIRA,
        body_format=BodyFormat.WIKI,
        url_label="Base URL",
        url_placeholder="https://jira.acme.com",
        default_url=None,
        destination_label="Project",
        destination_placeholder="SEC",
        has_issue_type=True,
        fields=(
            TrackerField(
                key="token",
                label="Personal access token",
                secret=True,
                help="Profile > Personal Access Tokens.",
            ),
        ),
        docs_url="https://confluence.atlassian.com/enterprise/using-personal-access-tokens-1026032365.html",
        body_limit=32_000,
        create_interval=0.3,
    ),
    TrackerSpec(
        kind=TrackerKind.GITHUB,
        label="GitHub Issues",
        family=TrackerFamily.GITHUB,
        body_format=BodyFormat.MARKDOWN,
        url_label="API URL",
        url_placeholder="https://api.github.com",
        default_url="https://api.github.com",
        destination_label="Repository",
        destination_placeholder="acme/security",
        has_issue_type=False,
        fields=(
            TrackerField(
                key="token",
                label="Fine-grained token",
                secret=True,
                help="Repository permissions > Issues: Read and write.",
            ),
        ),
        docs_url="https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens",
        body_limit=65_000,
        create_interval=1.0,
    ),
    TrackerSpec(
        kind=TrackerKind.GITLAB,
        label="GitLab Issues",
        family=TrackerFamily.GITLAB,
        body_format=BodyFormat.MARKDOWN,
        url_label="Instance URL",
        url_placeholder="https://gitlab.com",
        default_url="https://gitlab.com",
        destination_label="Project",
        destination_placeholder="acme/security",
        has_issue_type=False,
        fields=(
            TrackerField(
                key="token",
                label="Access token",
                secret=True,
                help="Project or personal token. Scope: api.",
            ),
        ),
        docs_url="https://docs.gitlab.com/user/profile/personal_access_tokens/",
        body_limit=100_000,
        create_interval=0.5,
    ),
)

TRACKERS_BY_KIND: dict[str, TrackerSpec] = {spec.kind.value: spec for spec in TRACKERS}
TRACKER_ORDER: tuple[str, ...] = tuple(spec.kind.value for spec in TRACKERS)


DESTINATION_PATTERNS: dict[str, re.Pattern[str]] = {
    TrackerFamily.JIRA.value: re.compile(r"^[A-Z][A-Z0-9_]{0,49}$"),
    TrackerFamily.GITHUB.value: re.compile(
        r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}$"
    ),
    TrackerFamily.GITLAB.value: re.compile(
        r"^[A-Za-z0-9_][A-Za-z0-9._-]*(?:/[A-Za-z0-9_][A-Za-z0-9._-]*){1,20}$"
    ),
}


def valid_destination(kind: str, value: str) -> bool:
    spec = TRACKERS_BY_KIND.get(kind)
    if spec is None or ".." in value:
        return False
    return bool(DESTINATION_PATTERNS[spec.family.value].match(value))


def secret_fields(kind: str) -> frozenset[str]:
    spec = TRACKERS_BY_KIND.get(kind)
    return frozenset(f.key for f in spec.fields if f.secret) if spec else frozenset()


class FilingState(StrEnum):
    PENDING = "pending"
    FILED = "filed"
    FAILED = "failed"


FILING_STATE_LABELS: dict[str, str] = {
    FilingState.PENDING.value: "Filing",
    FilingState.FILED.value: "Filed",
    FilingState.FAILED.value: "Not filed",
}


TICKETED_STATES: tuple[str, ...] = (FilingState.PENDING.value, FilingState.FILED.value)


class RemoteCategory(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


REMOTE_CATEGORY_ORDER: tuple[str, ...] = tuple(c.value for c in RemoteCategory)

REMOTE_CATEGORY_LABELS: dict[str, str] = {
    RemoteCategory.TODO.value: "To do",
    RemoteCategory.IN_PROGRESS.value: "In progress",
    RemoteCategory.DONE.value: "Done",
}

JIRA_CATEGORIES: dict[str, str] = {
    "new": RemoteCategory.TODO.value,
    "indeterminate": RemoteCategory.IN_PROGRESS.value,
    "done": RemoteCategory.DONE.value,
}


class Grouping(StrEnum):
    AUTO = "auto"
    SEPARATE = "separate"


GROUPING_LABELS: dict[str, str] = {
    Grouping.AUTO.value: "Group by check",
    Grouping.SEPARATE.value: "One issue per finding",
}

INDIVIDUAL_SEVERITIES: frozenset[str] = frozenset(
    {Severity.CRITICAL.value, Severity.HIGH.value}
)


def files_alone(severity: str, *, is_kev: bool, evidence: str) -> bool:
    """A finding that gets its own issue whatever the grouping."""
    return (
        severity in INDIVIDUAL_SEVERITIES or is_kev or evidence == Evidence.PROVEN.value
    )


class CommentKind(StrEnum):
    ADDED = "added"
    NOT_OBSERVED = "not_observed"
    OBSERVED_AGAIN = "observed_again"
    STILL_OBSERVED = "still_observed"


class CommentState(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
