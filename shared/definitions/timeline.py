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


# ---------- services ----------


class ServiceTimelineMode(StrEnum):
    ADDRESS = "address"
    PORT = "port"


SERVICE_STAGE = "port_scan"


class AddressState(StrEnum):
    SAME = "same"
    OPENED = "opened"
    CLOSED = "closed"
    BOTH = "both"
    FIRST = "first"
    GONE = "gone"
    UNCONFIRMED = "unconfirmed"
    UNOBSERVED = "unobserved"
    UNSEEN = "unseen"


ADDRESS_STATE_LABELS: dict[str, str] = {
    AddressState.SAME.value: "Same ports",
    AddressState.OPENED.value: "Port opened",
    AddressState.CLOSED.value: "Port closed",
    AddressState.BOTH.value: "Opened and closed",
    AddressState.FIRST.value: "First seen",
    AddressState.GONE.value: "Gone",
    AddressState.UNCONFIRMED.value: "Not confirmed",
    AddressState.UNOBSERVED.value: "Ports not scanned",
    AddressState.UNSEEN.value: "Not yet seen",
}


class LaneState(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    UNCONFIRMED = "unconfirmed"
    UNOBSERVED = "unobserved"
    UNSEEN = "unseen"


LANE_STATE_LABELS: dict[str, str] = {
    LaneState.OPEN.value: "Open",
    LaneState.CLOSED.value: "Closed",
    LaneState.UNCONFIRMED.value: "Not confirmed",
    LaneState.UNOBSERVED.value: "Ports not scanned",
    LaneState.UNSEEN.value: "Not yet seen",
}

SERVICE_OBSERVATION_LABELS: dict[str, str] = {
    Observation.OBSERVED.value: "Ports scanned",
    Observation.PARTIAL.value: "Port scan partial",
    Observation.UNOBSERVED.value: "Ports not scanned in this run",
}


class AddressFlag(StrEnum):
    OPENED = "opened"
    CLOSED = "closed"
    NEW = "new"
    GONE = "gone"
    SOFTWARE = "software"
    FLAPPING = "flapping"


ADDRESS_FLAG_ORDER: tuple[str, ...] = tuple(flag.value for flag in AddressFlag)

ADDRESS_FLAG_LABELS: dict[str, str] = {
    AddressFlag.OPENED.value: "Ports opened",
    AddressFlag.CLOSED.value: "Ports closed",
    AddressFlag.NEW.value: "New address",
    AddressFlag.GONE.value: "Gone",
    AddressFlag.SOFTWARE.value: "Software changed",
    AddressFlag.FLAPPING.value: "Keeps changing",
}

ADDRESS_FLAG_HELP: dict[str, str] = {
    AddressFlag.OPENED.value: "A port opened on the address inside the window.",
    AddressFlag.CLOSED.value: "A port closed on the address inside the window.",
    AddressFlag.NEW.value: "The address answered on a port for the first time in this scan.",
    AddressFlag.GONE.value: "No port answers on the address in this scan.",
    AddressFlag.SOFTWARE.value: "A service on the address reported different software.",
    AddressFlag.FLAPPING.value: "One port opened and closed three or more times in the window.",
}


class PortFlag(StrEnum):
    SPREAD = "spread"
    SHRANK = "shrank"
    NEW = "new"
    GONE = "gone"


PORT_FLAG_ORDER: tuple[str, ...] = tuple(flag.value for flag in PortFlag)

PORT_FLAG_LABELS: dict[str, str] = {
    PortFlag.SPREAD.value: "Spread",
    PortFlag.SHRANK.value: "Shrank",
    PortFlag.NEW.value: "New on target",
    PortFlag.GONE.value: "Gone",
}

PORT_FLAG_HELP: dict[str, str] = {
    PortFlag.SPREAD.value: "The port opened on more addresses inside the window.",
    PortFlag.SHRANK.value: "The port closed on some addresses inside the window.",
    PortFlag.NEW.value: "The port answered on this target for the first time in this scan.",
    PortFlag.GONE.value: "No address answers on the port in this scan.",
}


class AddressSort(StrEnum):
    LAST_CHANGE = "last_change"
    CHANGES = "changes"
    FIRST_SEEN = "first_seen"
    OPEN = "open"
    ADDRESS = "address"


class PortSort(StrEnum):
    ADDRESSES = "addresses"
    LAST_CHANGE = "last_change"
    FIRST_SEEN = "first_seen"
    PORT = "port"


# addresses named on a port cell
MAX_CELL_ADDRESSES = 8

# ---------- findings ----------


class FindingTimelineMode(StrEnum):
    LIFESPANS = "lifespans"
    CHECKS = "checks"


FINDING_MODE_LABELS: dict[str, str] = {
    FindingTimelineMode.LIFESPANS.value: "Lifespans",
    FindingTimelineMode.CHECKS.value: "By check",
}


class FindingState(StrEnum):
    OPEN = "open"
    REGRESSED = "regressed"
    FIXED = "fixed"
    NOT_TESTED = "not_tested"
    UNOBSERVED = "unobserved"
    UNSEEN = "unseen"


PRESENT_STATES: frozenset[str] = frozenset(
    {FindingState.OPEN.value, FindingState.REGRESSED.value}
)

FINDING_STATE_LABELS: dict[str, str] = {
    FindingState.OPEN.value: "Open",
    FindingState.REGRESSED.value: "Came back",
    FindingState.FIXED.value: "Fixed",
    FindingState.NOT_TESTED.value: "Not tested",
    FindingState.UNOBSERVED.value: "No vulnerability scan",
    FindingState.UNSEEN.value: "Not seen yet",
}

FINDING_OBSERVATION_LABELS: dict[str, str] = {
    Observation.PARTIAL.value: "Vulnerability scan incomplete",
    Observation.UNOBSERVED.value: "No vulnerability scan in this run",
}


class FindingGroup(StrEnum):
    REGRESSED = "regressed"
    NEW = "new"
    OPEN = "open"
    FIXED = "fixed"
    SET_ASIDE = "set_aside"


FINDING_GROUP_ORDER: tuple[str, ...] = tuple(group.value for group in FindingGroup)

FINDING_GROUP_LABELS: dict[str, str] = {
    FindingGroup.REGRESSED.value: "Regressed",
    FindingGroup.NEW.value: "New in this scan",
    FindingGroup.OPEN.value: "Open",
    FindingGroup.FIXED.value: "Fixed",
    FindingGroup.SET_ASIDE.value: "Set aside",
}

FINDING_GROUP_HELP: dict[str, str] = {
    FindingGroup.REGRESSED.value: "Came back after a run that found it fixed.",
    FindingGroup.NEW.value: "First seen in this scan.",
    FindingGroup.OPEN.value: "Found in this scan, or absent with the check untested since.",
    FindingGroup.FIXED.value: "A later run tested for it and found nothing.",
    FindingGroup.SET_ASIDE.value: "Reviewed as a false positive or an accepted risk.",
}


class FindingSort(StrEnum):
    AGE = "age"
    LAST_CHANGE = "last_change"
    SEVERITY = "severity"
    FIRST_SEEN = "first_seen"
    NAME = "name"


class CheckState(StrEnum):
    TESTED = "tested"
    NOT_TESTED = "not_tested"
    NOT_IN_LIBRARY = "not_in_library"
    UNOBSERVED = "unobserved"


CHECK_STATE_LABELS: dict[str, str] = {
    CheckState.TESTED.value: "Tested",
    CheckState.NOT_TESTED.value: "Not tested",
    CheckState.NOT_IN_LIBRARY.value: "Check not in the library yet",
    CheckState.UNOBSERVED.value: "No vulnerability scan",
}


class CheckFlag(StrEnum):
    SPREAD = "spread"
    SHRANK = "shrank"
    CLEARED = "cleared"
    LIBRARY_NEW = "library_new"


CHECK_FLAG_ORDER: tuple[str, ...] = tuple(flag.value for flag in CheckFlag)

CHECK_FLAG_LABELS: dict[str, str] = {
    CheckFlag.SPREAD.value: "Spread",
    CheckFlag.SHRANK.value: "Shrank",
    CheckFlag.CLEARED.value: "Cleared",
    CheckFlag.LIBRARY_NEW.value: "New to the library",
}

CHECK_FLAG_HELP: dict[str, str] = {
    CheckFlag.SPREAD.value: "The check matches more web assets than in the first run of the window that found it.",
    CheckFlag.SHRANK.value: "The check matches fewer web assets than in the first run of the window that found it.",
    CheckFlag.CLEARED.value: "No web asset carries the finding in this scan.",
    CheckFlag.LIBRARY_NEW.value: "The library gained the check inside the window.",
}


class CheckSort(StrEnum):
    HOSTS = "hosts"
    SEVERITY = "severity"
    LAST_CHANGE = "last_change"
    NAME = "name"


# findings the Timeline reads before it asks for a narrower query
MAX_TIMELINE_FINDINGS = 5000
# hosts named on a check cell
MAX_CELL_HOSTS = MAX_CELL_ADDRESSES


__all__ = [
    "ABSENT_STATES",
    "ADDRESS_FLAG_HELP",
    "ADDRESS_FLAG_LABELS",
    "ADDRESS_FLAG_ORDER",
    "ADDRESS_STATE_LABELS",
    "CAPTURED_STATES",
    "CHECK_FLAG_HELP",
    "CHECK_FLAG_LABELS",
    "CHECK_FLAG_ORDER",
    "CHECK_STATE_LABELS",
    "DEFAULT_TIMELINE_WINDOW",
    "FINDING_GROUP_HELP",
    "FINDING_GROUP_LABELS",
    "FINDING_GROUP_ORDER",
    "FINDING_MODE_LABELS",
    "FINDING_OBSERVATION_LABELS",
    "FINDING_STATE_LABELS",
    "FLAG_HELP",
    "FLAG_LABELS",
    "FLAG_ORDER",
    "FLAPPING_TRANSITIONS",
    "LANE_STATE_LABELS",
    "MAX_CELL_ADDRESSES",
    "MAX_CELL_HOSTS",
    "MAX_TIMELINE_FINDINGS",
    "MAX_TIMELINE_SCANS",
    "OBSERVATION_LABELS",
    "PORT_FLAG_HELP",
    "PORT_FLAG_LABELS",
    "PORT_FLAG_ORDER",
    "PRESENT_STATES",
    "RENDER_FLAG_HELP",
    "RENDER_FLAG_LABELS",
    "RENDER_FLAG_ORDER",
    "RENDER_OBSERVATION_LABELS",
    "RENDER_STAGE",
    "RENDER_STATE_LABELS",
    "SERVICE_OBSERVATION_LABELS",
    "SERVICE_STAGE",
    "TIMELINE_WINDOWS",
    "WEB_ATTRIBUTES",
    "WEB_ATTRIBUTE_LABELS",
    "WEB_STATE_LABELS",
    "AddressFlag",
    "AddressSort",
    "AddressState",
    "CheckFlag",
    "CheckSort",
    "CheckState",
    "FindingGroup",
    "FindingSort",
    "FindingState",
    "FindingTimelineMode",
    "LaneState",
    "Observation",
    "PortFlag",
    "PortSort",
    "RenderFlag",
    "RenderSort",
    "RenderState",
    "ServiceTimelineMode",
    "TimelineFlag",
    "TimelineSort",
    "WebAssetState",
]
