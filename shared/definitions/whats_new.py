"""What is new: surface that appeared since the operator last caught up."""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum

from shared.definitions.bounty_programs import SOURCE_LABELS as PROGRAM_SOURCE_LABELS
from shared.definitions.bounty_programs import BountyEvent
from shared.definitions.correlation import SCREENSHOT_DISTANCE
from shared.definitions.watch import CT_SOURCE


class NewKind(StrEnum):
    FINDING = "finding"
    PROGRAM = "program"
    SCOPE = "scope"
    OUT_OF_SCOPE = "out_of_scope"
    BOUNTY_TABLE = "bounty_table"
    RULES = "rules"
    CERT_HOST = "cert_host"
    TARGET = "target"


KIND_ORDER: tuple[str, ...] = tuple(k.value for k in NewKind)

TERMS_KINDS: frozenset[str] = frozenset(
    {NewKind.BOUNTY_TABLE.value, NewKind.RULES.value}
)


class NewBasis(StrEnum):
    MARK = "mark"
    WINDOW = "window"
    DAYS = "days"


class SubjectKind(StrEnum):
    RUN = "run"
    PROGRAM = "program"
    LIBRARY = "library"
    TARGETS = "targets"


class ProgramRing(StrEnum):
    ENGAGED = "engaged"
    LIBRARY = "library"


class NewTone(StrEnum):
    NEW = "new"
    HOT = "hot"


NEW_WINDOWS: dict[str, timedelta] = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}
DEFAULT_NEW_WINDOW = "7d"
GRID_DAYS = 91
BOUNTY_ROWS_PER_SECTION = 50
GROUP_LIMIT = 80
EVIDENCE_FINDINGS = 4
MAX_TEXT_FILTER = 200
DEFAULT_ZONE = "UTC"
WATCH_SOURCE = "watch"
SCOPE_SOURCE = "scope"

SOURCE_LABELS: dict[str, str] = {
    **PROGRAM_SOURCE_LABELS,
    CT_SOURCE: "Certificate log",
    WATCH_SOURCE: "Program watch",
    SCOPE_SOURCE: "Program scope",
}

SCOPE_EVENTS: frozenset[str] = frozenset(
    {BountyEvent.SCOPE_ADDED.value, BountyEvent.CAME_INTO_SCOPE.value}
)
PROGRAM_EVENTS: frozenset[str] = frozenset(
    {
        BountyEvent.PROGRAM_ADDED.value,
        BountyEvent.PROGRAM_WENT_PUBLIC.value,
        BountyEvent.SUBMISSIONS_OPENED.value,
        BountyEvent.BOUNTIES_STARTED.value,
    }
)
GONE_EVENTS: frozenset[str] = frozenset(
    {BountyEvent.SCOPE_REMOVED.value, BountyEvent.WENT_OUT_OF_SCOPE.value}
)
BOUNTY_TABLE_EVENTS: frozenset[str] = frozenset(
    {BountyEvent.PAYOUT_CHANGED.value, BountyEvent.ASSET_BOUNTY_CHANGED.value}
)
RULES_EVENTS: frozenset[str] = frozenset(
    {BountyEvent.RULES_CHANGED.value, BountyEvent.ASSET_RULES_CHANGED.value}
)
ENGAGED_EVENTS: frozenset[str] = (
    SCOPE_EVENTS | GONE_EVENTS | BOUNTY_TABLE_EVENTS | RULES_EVENTS
)

EVENT_KIND: dict[str, str] = {
    **dict.fromkeys(SCOPE_EVENTS, NewKind.SCOPE.value),
    **dict.fromkeys(PROGRAM_EVENTS, NewKind.PROGRAM.value),
    **dict.fromkeys(GONE_EVENTS, NewKind.OUT_OF_SCOPE.value),
    **dict.fromkeys(BOUNTY_TABLE_EVENTS, NewKind.BOUNTY_TABLE.value),
    **dict.fromkeys(RULES_EVENTS, NewKind.RULES.value),
}


VISUAL_DISTANCE = SCREENSHOT_DISTANCE
VISUAL_LIMIT = 300
VISUAL_FIELDS: tuple[str, ...] = ("http_status", "page_title", "tech", "webserver")


class Fact(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    KEV = "kev"
    NOT_TARGET = "not_target"
    ANSWERING = "answering"
    NOT_SCANNED = "not_scanned"


def mark_key(project_id) -> str:
    return f"whats_new:{project_id}"
