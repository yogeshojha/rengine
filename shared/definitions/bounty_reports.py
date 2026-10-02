"""A researcher's own reports and bounties on a platform with a researcher API."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from shared.definitions.bounty_programs import MAX_SEVERITIES


class ReportStage(Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    CLOSED = "closed"


REPORT_STAGE_LABELS: dict[str, str] = {
    ReportStage.OPEN.value: "Open",
    ReportStage.RESOLVED.value: "Resolved",
    ReportStage.CLOSED.value: "Closed",
}


@dataclass(frozen=True)
class ReportStateSpec:
    key: str
    label: str
    stage: ReportStage


REPORT_STATES: tuple[ReportStateSpec, ...] = (
    ReportStateSpec("new", "New", ReportStage.OPEN),
    ReportStateSpec("pending-program-review", "Pending review", ReportStage.OPEN),
    ReportStateSpec("triaged", "Triaged", ReportStage.OPEN),
    ReportStateSpec("needs-more-info", "Needs more info", ReportStage.OPEN),
    ReportStateSpec("retesting", "Retesting", ReportStage.OPEN),
    ReportStateSpec("resolved", "Resolved", ReportStage.RESOLVED),
    ReportStateSpec("duplicate", "Duplicate", ReportStage.CLOSED),
    ReportStateSpec("informative", "Informative", ReportStage.CLOSED),
    ReportStateSpec("not-applicable", "Not applicable", ReportStage.CLOSED),
    ReportStateSpec("spam", "Spam", ReportStage.CLOSED),
)

REPORT_STATES_BY_KEY: dict[str, ReportStateSpec] = {s.key: s for s in REPORT_STATES}


class ReportSort(Enum):
    SUBMITTED = "submitted"
    BOUNTY = "bounty"
    SEVERITY = "severity"
    PROGRAM = "program"


def stage_states(stage: str) -> list[str]:
    return [s.key for s in REPORT_STATES if s.stage.value == stage]


SETTLED_STATES: tuple[str, ...] = tuple(
    s.key for s in REPORT_STATES if s.stage is not ReportStage.OPEN
)


REPORT_SEVERITIES: tuple[str, ...] = MAX_SEVERITIES

MAX_REPORT_TITLE = 500
MAX_WEAKNESS = 200
MAX_CURRENCY = 8


def report_state(raw: str | None) -> ReportStateSpec:
    """The state spec, with an unlisted platform state kept open under its own name."""
    value = (raw or "").strip().lower()
    return REPORT_STATES_BY_KEY.get(
        value,
        ReportStateSpec(
            value, value.replace("-", " ").capitalize() or "Unknown", ReportStage.OPEN
        ),
    )


def report_severity(raw: str | None) -> str | None:
    value = (raw or "").strip().lower()
    return value if value in REPORT_SEVERITIES else None
