"""Connector vocabulary: states, source tools, notice kinds and actions."""

from __future__ import annotations

from enum import StrEnum

from shared.definitions.vulnerabilities import Severity

MAX_NAME = 80
MAX_BATCH = 500
MAX_QUEUE = 5000
MAX_BODY_SAMPLE = 4000
MAX_CANDIDATE_SCAN = 200
LIVE_MINUTES = 2
PRESENCE_SECONDS = 15


class ConnectorKind(StrEnum):
    BURP = "burp"


class SetupControl(StrEnum):
    """The control a setup step carries."""

    DOWNLOAD = "download"
    CREDENTIALS = "credentials"


class ConnectorState(StrEnum):
    IDLE = "idle"
    LIVE = "live"
    CONNECTED = "connected"
    STALE = "stale"
    PAUSED = "paused"


class SourceTool(StrEnum):
    """The proxy tool that produced the request."""

    PROXY = "proxy"
    REPEATER = "repeater"
    OTHER = "other"


INGESTED_TOOLS: frozenset[str] = frozenset(
    {SourceTool.PROXY.value, SourceTool.REPEATER.value}
)

MAX_PICKER_TARGETS = 500
MAX_SCOPE_HOSTS = 500
MAX_NOTICE_BATCH = 25
MANUAL_RUN_LABEL = "Manual testing"
BROWSING_RUN_LABEL = "Browsing"


class ActionKind(StrEnum):
    """The proxy tool a request is handed to."""

    REPEATER = "repeater"
    INTRUDER = "intruder"
    ORGANIZER = "organizer"
    SITE_MAP = "sitemap"


ACTION_KIND_LABELS: dict[str, str] = {
    ActionKind.REPEATER.value: "Repeater",
    ActionKind.INTRUDER.value: "Intruder",
    ActionKind.ORGANIZER.value: "Organizer",
    ActionKind.SITE_MAP.value: "Site map",
}

HANDOFF_KINDS: tuple[str, ...] = tuple(k.value for k in ActionKind)
DEFAULT_ACTION_KIND = ActionKind.REPEATER.value

MAX_PENDING_ACTIONS = 200
MAX_ACTION_BATCH = 50
ACTION_TTL_MINUTES = 60
MAX_HANDOFF_REQUEST = 64_000
MAX_HANDOFF_RESPONSE = 100_000
MAX_HANDOFF_NOTES = 2000
HANDOFF_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) reNgine"


class HighlightColor(StrEnum):
    """Burp's highlight names."""

    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    BLUE = "blue"
    GRAY = "gray"


SEVERITY_HIGHLIGHT: dict[str, str] = {
    Severity.CRITICAL.value: HighlightColor.RED.value,
    Severity.HIGH.value: HighlightColor.ORANGE.value,
    Severity.MEDIUM.value: HighlightColor.YELLOW.value,
    Severity.LOW.value: HighlightColor.BLUE.value,
    Severity.INFO.value: HighlightColor.GRAY.value,
    Severity.UNKNOWN.value: HighlightColor.GRAY.value,
}


class CandidateState(StrEnum):
    NEW = "new"
    QUEUED = "queued"
    SCANNED = "scanned"
    IGNORED = "ignored"


class NoticeKind(StrEnum):
    """Why a shape was flagged."""

    SENSITIVE = "sensitive"
    ADMIN = "admin"
    UNSEEN_BY_SCANS = "unseen_by_scans"
    NEW_PARAMS = "new_params"
    SERVER_ERROR = "server_error"
    NON_STANDARD_METHOD = "non_standard_method"
    OUT_OF_SCOPE = "out_of_scope"


NOTICE_LABELS: dict[str, str] = {
    NoticeKind.SENSITIVE.value: "Sensitive path",
    NoticeKind.ADMIN.value: "Administrative interface",
    NoticeKind.UNSEEN_BY_SCANS.value: "Not found by any scan",
    NoticeKind.NEW_PARAMS.value: "Parameters not seen by scans",
    NoticeKind.SERVER_ERROR.value: "Server error",
    NoticeKind.NON_STANDARD_METHOD.value: "Uncommon method",
    NoticeKind.OUT_OF_SCOPE.value: "Out of scope",
}

# a notice in this set surfaces the row on its own
LOUD_NOTICES: frozenset[str] = frozenset(
    {
        NoticeKind.SENSITIVE.value,
        NoticeKind.ADMIN.value,
        NoticeKind.SERVER_ERROR.value,
        NoticeKind.OUT_OF_SCOPE.value,
    }
)

NOTICE_ORDER: tuple[str, ...] = (
    NoticeKind.OUT_OF_SCOPE.value,
    NoticeKind.SENSITIVE.value,
    NoticeKind.SERVER_ERROR.value,
    NoticeKind.ADMIN.value,
)

SAFE_METHODS: frozenset[str] = frozenset({"GET", "HEAD", "OPTIONS"})
COMMON_METHODS: frozenset[str] = frozenset(
    {"GET", "POST", "HEAD", "OPTIONS", "PUT", "PATCH", "DELETE"}
)


def presence_key(connector_id) -> str:
    return f"connector:online:{connector_id}"


def state_for(minutes_since: float | None, paused: bool, online: bool = False) -> str:
    if paused:
        return ConnectorState.PAUSED.value
    if minutes_since is not None and minutes_since <= LIVE_MINUTES:
        return ConnectorState.LIVE.value
    if online:
        return ConnectorState.CONNECTED.value
    if minutes_since is None:
        return ConnectorState.IDLE.value
    return ConnectorState.STALE.value
