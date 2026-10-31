"""What a cell says about an asset at one scan, and what a row says over a window."""

from __future__ import annotations

from enum import StrEnum

from shared.definitions.compare import WATCHED_FIELDS
from shared.definitions.surface import SurfaceDimension


class WebAssetState(StrEnum):
    LIVE = "live"
    REDIRECT = "redirect"
    CLIENT_ERROR = "client_error"
    SERVER_ERROR = "server_error"
    NO_HTTP = "no_http"
    UNRESOLVED = "unresolved"
    GONE = "gone"
    UNCONFIRMED = "unconfirmed"
    UNOBSERVED = "unobserved"
    UNSEEN = "unseen"


# no row, and the run looked
ABSENT_STATES: frozenset[str] = frozenset(
    {WebAssetState.GONE.value, WebAssetState.UNSEEN.value}
)

WEB_STATE_LABELS: dict[str, str] = {
    WebAssetState.LIVE.value: "Live",
    WebAssetState.REDIRECT.value: "Redirect",
    WebAssetState.CLIENT_ERROR.value: "Client error",
    WebAssetState.SERVER_ERROR.value: "Server error",
    WebAssetState.NO_HTTP.value: "No HTTP",
    WebAssetState.UNRESOLVED.value: "Unresolved",
    WebAssetState.GONE.value: "Gone",
    WebAssetState.UNCONFIRMED.value: "Not confirmed",
    WebAssetState.UNOBSERVED.value: "Not observed",
    WebAssetState.UNSEEN.value: "Not yet seen",
}


class Observation(StrEnum):
    """How far a run's observing stages got."""

    OBSERVED = "observed"
    PARTIAL = "partial"
    UNOBSERVED = "unobserved"


OBSERVATION_LABELS: dict[str, str] = {
    Observation.OBSERVED.value: "Observed",
    Observation.PARTIAL.value: "Discovery partial",
    Observation.UNOBSERVED.value: "Not observed",
}


class TimelineFlag(StrEnum):
    NEW = "new"
    GONE = "gone"
    CHANGED = "changed"
    EPHEMERAL = "ephemeral"
    FLAPPING = "flapping"
    ATTRIBUTE = "attribute"


FLAG_ORDER: tuple[str, ...] = tuple(flag.value for flag in TimelineFlag)

FLAG_LABELS: dict[str, str] = {
    TimelineFlag.NEW.value: "New in this scan",
    TimelineFlag.GONE.value: "Gone",
    TimelineFlag.CHANGED.value: "Changed",
    TimelineFlag.EPHEMERAL.value: "Ephemeral",
    TimelineFlag.FLAPPING.value: "Flapping",
    TimelineFlag.ATTRIBUTE.value: "Attribute changed",
}

FLAG_HELP: dict[str, str] = {
    TimelineFlag.NEW.value: "First seen in this scan.",
    TimelineFlag.GONE.value: "Absent from this scan after an earlier sighting.",
    TimelineFlag.CHANGED.value: "At least one transition in the window.",
    TimelineFlag.EPHEMERAL.value: "Appeared and gone inside the window.",
    TimelineFlag.FLAPPING.value: "Three or more state transitions in the window.",
    TimelineFlag.ATTRIBUTE.value: "Title, address, redirect, server, WAF, CDN or certificate changed with the state unchanged.",
}

TIMELINE_WINDOWS: tuple[int, ...] = (10, 25, 50)
DEFAULT_TIMELINE_WINDOW = 25
MAX_TIMELINE_SCANS = TIMELINE_WINDOWS[-1]
FLAPPING_TRANSITIONS = 3

# changes the fill cannot show, drawn as a dot
WEB_ATTRIBUTES: tuple[str, ...] = (
    "page_title",
    "final_url",
    "resolved_ips",
    "cname",
    "webserver",
    "waf",
    "cdn_name",
    "tls_expired",
)

WEB_ATTRIBUTE_LABELS: dict[str, str] = {
    field.name: field.label
    for field in WATCHED_FIELDS[SurfaceDimension.WEB_ASSETS.value]
    if field.name in WEB_ATTRIBUTES
}


class TimelineSort(StrEnum):
    LAST_CHANGE = "last_change"
    CHANGES = "changes"
    FIRST_SEEN = "first_seen"
    NAME = "name"
    STATUS = "status"


# ---------- renders ----------


class RenderState(StrEnum):
    FIRST = "first"
    CHANGED = "changed"
    SAME = "same"
    NOT_CAPTURED = "not_captured"
    NO_HTTP = "no_http"
    GONE = "gone"
    UNCONFIRMED = "unconfirmed"
    UNOBSERVED = "unobserved"
    UNSEEN = "unseen"


CAPTURED_STATES: frozenset[str] = frozenset(
    {RenderState.FIRST.value, RenderState.CHANGED.value, RenderState.SAME.value}
)

RENDER_STATE_LABELS: dict[str, str] = {
    RenderState.FIRST.value: "First screenshot",
    RenderState.CHANGED.value: "Changed",
    RenderState.SAME.value: "Unchanged",
    RenderState.NOT_CAPTURED.value: "No screenshot",
    RenderState.NO_HTTP.value: "No HTTP",
    RenderState.GONE.value: "Gone",
    RenderState.UNCONFIRMED.value: "Not confirmed",
    RenderState.UNOBSERVED.value: "Not observed",
    RenderState.UNSEEN.value: "Not yet seen",
}

RENDER_OBSERVATION_LABELS: dict[str, str] = {
    Observation.OBSERVED.value: "Observed",
    Observation.PARTIAL.value: "Some screenshots missing",
    Observation.UNOBSERVED.value: "No screenshots in this run",
}

RENDER_STAGE = "screenshot"


class RenderFlag(StrEnum):
    NEW = "new"
    CHANGED = "changed"
    FLAPPING = "flapping"
    EXPIRED = "expired"
    NOT_CAPTURED = "not_captured"


RENDER_FLAG_ORDER: tuple[str, ...] = tuple(flag.value for flag in RenderFlag)

RENDER_FLAG_LABELS: dict[str, str] = {
    RenderFlag.NEW.value: "First screenshot",
    RenderFlag.CHANGED.value: "Changed",
    RenderFlag.FLAPPING.value: "Keeps changing",
    RenderFlag.EXPIRED.value: "Image removed",
    RenderFlag.NOT_CAPTURED.value: "No screenshot",
}

RENDER_FLAG_HELP: dict[str, str] = {
    RenderFlag.NEW.value: "The first screenshot of this web asset was taken in this scan.",
    RenderFlag.CHANGED.value: "The page looked different in at least one run of the window.",
    RenderFlag.FLAPPING.value: "The page looked different three or more times in the window.",
    RenderFlag.EXPIRED.value: "Retention removed an older image in the window.",
    RenderFlag.NOT_CAPTURED.value: "Answered HTTP in this scan with no screenshot taken.",
}


class RenderSort(StrEnum):
    LAST_CHANGE = "last_change"
    CHANGES = "changes"
    FIRST_CAPTURED = "first_captured"
    NAME = "name"
    STATUS = "status"


__all__ = [
    "ABSENT_STATES",
    "CAPTURED_STATES",
    "DEFAULT_TIMELINE_WINDOW",
    "FLAG_HELP",
    "FLAG_LABELS",
    "FLAG_ORDER",
    "FLAPPING_TRANSITIONS",
    "MAX_TIMELINE_SCANS",
    "OBSERVATION_LABELS",
    "RENDER_FLAG_HELP",
    "RENDER_FLAG_LABELS",
    "RENDER_FLAG_ORDER",
    "RENDER_OBSERVATION_LABELS",
    "RENDER_STAGE",
    "RENDER_STATE_LABELS",
    "TIMELINE_WINDOWS",
    "WEB_ATTRIBUTES",
    "WEB_ATTRIBUTE_LABELS",
    "WEB_STATE_LABELS",
    "Observation",
    "RenderFlag",
    "RenderSort",
    "RenderState",
    "TimelineFlag",
    "TimelineSort",
    "WebAssetState",
]
