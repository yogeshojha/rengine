"""Connector vocabulary: states, source tools, notice kinds and actions."""

from __future__ import annotations

from enum import StrEnum

from shared.definitions.vulnerabilities import Severity

MAX_NAME = 80
MAX_CONNECTORS = 20
MAX_BATCH = 500
MAX_QUEUE = 5000
MAX_BODY_SAMPLE = 4000
MAX_CANDIDATE_SCAN = 200
STALE_MINUTES = 30
LIVE_MINUTES = 2


class ConnectorKind(StrEnum):
    BURP = "burp"


class ConnectorState(StrEnum):
    IDLE = "idle"
    LIVE = "live"
    STALE = "stale"
    PAUSED = "paused"


CONNECTOR_STATE_LABELS: dict[str, str] = {
    ConnectorState.IDLE.value: "Not connected",
    ConnectorState.LIVE.value: "Receiving",
    ConnectorState.STALE.value: "Idle",
    ConnectorState.PAUSED.value: "Paused",
}


class SourceTool(StrEnum):
    """The proxy tool that produced the request."""

    PROXY = "proxy"
    REPEATER = "repeater"
    OTHER = "other"


SOURCE_TOOL_LABELS: dict[str, str] = {
    SourceTool.PROXY.value: "Proxy",
    SourceTool.REPEATER.value: "Repeater",
    SourceTool.OTHER.value: "Other",
}

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

ACTION_KIND_HELP: dict[str, str] = {
    ActionKind.REPEATER.value: "One tab per request.",
    ActionKind.INTRUDER.value: "One attack per request.",
    ActionKind.ORGANIZER.value: "Request and response, with the finding as a note.",
    ActionKind.SITE_MAP.value: "Request and response under the host in Target.",
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


CANDIDATE_STATE_LABELS: dict[str, str] = {
    CandidateState.NEW.value: "New",
    CandidateState.QUEUED.value: "Queued",
    CandidateState.SCANNED.value: "Scanned",
    CandidateState.IGNORED.value: "Ignored",
}


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

NOTICE_HELP: dict[str, str] = {
    NoticeKind.SENSITIVE.value: "The path matches a pattern associated with sensitive files.",
    NoticeKind.ADMIN.value: "The path matches an administrative or authentication surface.",
    NoticeKind.UNSEEN_BY_SCANS.value: "A scan covered this target and did not record this path.",
    NoticeKind.NEW_PARAMS.value: "A scan recorded this path with a different parameter set.",
    NoticeKind.SERVER_ERROR.value: "The server returned a 5xx response.",
    NoticeKind.NON_STANDARD_METHOD.value: "The method is not GET, POST, HEAD or OPTIONS.",
    NoticeKind.OUT_OF_SCOPE.value: "A bug bounty program lists this host as out of scope.",
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


def state_for(minutes_since: float | None, paused: bool) -> str:
    if paused:
        return ConnectorState.PAUSED.value
    if minutes_since is None:
        return ConnectorState.IDLE.value
    if minutes_since <= LIVE_MINUTES:
        return ConnectorState.LIVE.value
    if minutes_since <= STALE_MINUTES:
        return ConnectorState.STALE.value
    return ConnectorState.IDLE.value
