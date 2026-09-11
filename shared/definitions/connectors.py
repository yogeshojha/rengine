"""Connector vocabulary: import scope, sync triggers and notice kinds."""

from __future__ import annotations

from enum import StrEnum

MAX_NAME = 80
MAX_CONNECTORS = 20
MAX_BATCH = 500
MAX_QUEUE = 5000
MAX_BODY_SAMPLE = 4000
MAX_CANDIDATE_SCAN = 200
# a connector with no traffic for this long is reported stale rather than live
STALE_MINUTES = 30
LIVE_MINUTES = 2
DEFAULT_QUIET_MINUTES = 5
DEFAULT_QUEUE_THRESHOLD = 25


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
    SourceTool.REPEATER.value: "Manual request",
    SourceTool.OTHER.value: "Other",
}

# manual requests are inventory; fuzzer and scanner payloads are not
INGESTED_TOOLS: frozenset[str] = frozenset(
    {SourceTool.PROXY.value, SourceTool.REPEATER.value}
)


class SyncTrigger(StrEnum):
    """Conditions under which the queue is scanned."""

    MANUAL = "manual"
    QUIET = "quiet"
    WALKED_AWAY = "walked_away"
    SESSION_END = "session_end"


SYNC_TRIGGER_LABELS: dict[str, str] = {
    SyncTrigger.MANUAL.value: "Manual",
    SyncTrigger.QUIET.value: "After a quiet period",
    SyncTrigger.WALKED_AWAY.value: "On host change",
    SyncTrigger.SESSION_END.value: "On disconnect",
}

SYNC_TRIGGER_HELP: dict[str, str] = {
    SyncTrigger.MANUAL.value: "The queue is scanned only on request.",
    SyncTrigger.QUIET.value: "Scans a host's queue once the quiet period elapses with no further traffic to that host.",
    SyncTrigger.WALKED_AWAY.value: "Scans a host's queue once traffic moves to a different host.",
    SyncTrigger.SESSION_END.value: "Scans the queue when the connector disconnects.",
}


MAX_PICKER_TARGETS = 500
# a proxy scope with thousands of entries is slower than no scope at all
MAX_SCOPE_HOSTS = 500
MAX_NOTICE_BATCH = 25
MANUAL_RUN_LABEL = "Manual testing"


class ActionKind(StrEnum):
    """Work reNgine hands back to the proxy."""

    REPEATER = "repeater"


ACTION_KIND_LABELS: dict[str, str] = {
    ActionKind.REPEATER.value: "Send to Repeater",
}

MAX_PENDING_ACTIONS = 200
MAX_ACTION_BATCH = 50
# an action nobody collected is stale; a proxy that reconnects should not replay yesterday
ACTION_TTL_MINUTES = 60


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
    """Why a shape was flagged, derived without sending a request.

    Whether a request carried a session is a fact on the row, not a flag: it is true of
    most traffic and says nothing on its own.
    """

    SENSITIVE = "sensitive"
    ADMIN = "admin"
    UNSEEN_BY_SCANS = "unseen_by_scans"
    SERVER_ERROR = "server_error"
    NON_STANDARD_METHOD = "non_standard_method"
    OUT_OF_SCOPE = "out_of_scope"


NOTICE_LABELS: dict[str, str] = {
    NoticeKind.SENSITIVE.value: "Sensitive path",
    NoticeKind.ADMIN.value: "Administrative interface",
    NoticeKind.UNSEEN_BY_SCANS.value: "Not found by any scan",
    NoticeKind.SERVER_ERROR.value: "Server error",
    NoticeKind.NON_STANDARD_METHOD.value: "Uncommon method",
    NoticeKind.OUT_OF_SCOPE.value: "Out of scope",
}

NOTICE_HELP: dict[str, str] = {
    NoticeKind.SENSITIVE.value: "The path matches a pattern associated with sensitive files.",
    NoticeKind.ADMIN.value: "The path matches an administrative or authentication surface.",
    NoticeKind.UNSEEN_BY_SCANS.value: "No scan of this target has recorded this request shape.",
    NoticeKind.SERVER_ERROR.value: "The server returned a 5xx response.",
    NoticeKind.NON_STANDARD_METHOD.value: "The method is not GET, POST, HEAD or OPTIONS.",
    NoticeKind.OUT_OF_SCOPE.value: "A bug bounty program lists this host as out of scope. Testing it is not authorised.",
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

# loudest first: what a tester is told when a shape carries several
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

# request headers that carry a session, in the order a connector should report them
AUTH_HEADERS: tuple[str, ...] = (
    "authorization",
    "cookie",
    "x-api-key",
    "x-auth-token",
    "x-csrf-token",
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
