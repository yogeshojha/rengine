from collections.abc import Sequence

from shared.definitions.notifications import ScanDeltas
from shared.definitions.stage_counts import Label, noun
from shared.definitions.surface import SurfaceDimension
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.utils.datetime import duration_text
from shared.utils.text import counted

FEED_EVENTS: tuple[ActivityEvent, ...] = (
    ActivityEvent.SCAN_COMPLETED,
    ActivityEvent.SCAN_FAILED,
    ActivityEvent.SCAN_CANCELLED,
    ActivityEvent.SCAN_PAUSED,
    ActivityEvent.SCAN_RESUMED,
    ActivityEvent.ISSUE_FILED,
    ActivityEvent.ISSUE_FAILED,
    ActivityEvent.TARGET_CREATED,
    ActivityEvent.TARGET_BULK_IMPORTED,
)

NAMES_SHOWN = 3
WATCH_ADDED = "Added by a program watch"
ERROR_CHARS = 300

_VULN = SurfaceDimension.VULNERABILITIES
_WEB = SurfaceDimension.WEB_ASSETS
_SERVICES = SurfaceDimension.SERVICES
_SECRETS = SurfaceDimension.SECRETS
_ENDPOINTS = SurfaceDimension.ENDPOINTS
_KEPT: tuple[tuple[str, Label], ...] = (
    ("vulnerabilities_found", noun(_VULN)),
    ("subdomains_found", noun(_WEB)),
    ("open_ports_found", noun(_SERVICES)),
    ("endpoints_found", noun(_ENDPOINTS)),
)


def _count(n: int, label: Label) -> str:
    return f"{n:,} {label[0] if n == 1 else label[1]}"


def _join(parts: Sequence[str | None]) -> str | None:
    return " · ".join(p for p in parts if p) or None


def _risk(d: ScanDeltas) -> tuple[str, ActivityLevel] | None:
    new = "new" if d.baseline else ""
    lead = f"{new} " if new else ""
    findings = (
        d.new_vulnerabilities if d.baseline else sum(d.vulnerability_counts.values())
    )
    if d.critical:
        return f"{d.critical:,} {lead}critical", ActivityLevel.ERROR
    if d.kev:
        return f"{d.kev:,} known exploited", ActivityLevel.ERROR
    if d.high:
        return f"{d.high:,} {lead}high", ActivityLevel.WARNING
    if d.new_secrets:
        return _count(d.new_secrets, noun(_SECRETS, before=new)), ActivityLevel.WARNING
    if findings:
        return _count(findings, noun(_VULN, before=new)), ActivityLevel.INFO
    return None


def _surface(counts: dict, d: ScanDeltas) -> str | None:
    if d.baseline:
        if d.new_hosts:
            return _count(d.new_hosts, noun(_WEB, before="new"))
        if d.new_services:
            return _count(d.new_services, noun(_SERVICES, before="new"))
        return None
    if n := counts.get("subdomains_found"):
        return _count(n, noun(_WEB))
    if n := counts.get("open_ports_found"):
        return _count(n, noun(_SERVICES))
    return None


def run_completed(
    counts: dict, deltas: ScanDeltas, seconds: float | None, label: str | None = None
) -> tuple[str, str | None, ActivityLevel]:
    """The run's worst new fact, then its growth, its label and its duration."""
    risk = _risk(deltas)
    surface = _surface(counts, deltas)
    facts = [f for f in (risk[0] if risk else None, surface) if f]
    if risk:
        level = risk[1]
    else:
        level = ActivityLevel.INFO if surface else ActivityLevel.SUCCESS
    title = facts[0] if facts else ("No changes" if deltas.baseline else "No results")
    description = _join(
        [
            *facts[1:],
            None if deltas.baseline else "first run",
            label,
            duration_text(seconds) if seconds else None,
        ]
    )
    return title, description, level


def run_failed(stage: str | None, error: str | None) -> str:
    text = " ".join((error or "One or more stages failed").split())[:ERROR_CHARS]
    return f"{stage}: {text}" if stage else text


def cancelled_reason(actor: str | None) -> str:
    return f"Cancelled by {actor}." if actor else "Cancelled."


def run_cancelled(reason: str | None, seconds: float | None, counts: dict) -> str:
    head = (
        reason.rstrip(".") if reason and reason.startswith("Cancelled") else "Cancelled"
    )
    head = f"{head} after {duration_text(seconds)}" if seconds else head
    kept = next(
        (_count(n, label) for col, label in _KEPT if (n := counts.get(col))), None
    )
    return f"{head} · {kept} kept" if kept else head


def run_paused(done: int, total: int) -> str:
    return f"{done} of {total} stages done"


def targets_added(
    values: Sequence[str], verb: str, *, skipped: int = 0, failed: int = 0
) -> tuple[str, str | None]:
    title = (
        f"{counted(len(values), 'target')} {verb}" if values else f"No targets {verb}"
    )
    shown = ", ".join(values[:NAMES_SHOWN])
    if len(values) > NAMES_SHOWN:
        shown += f" and {len(values) - NAMES_SHOWN:,} more"
    return title, _join(
        [
            shown,
            f"{skipped:,} skipped" if skipped else None,
            f"{failed:,} failed" if failed else None,
        ]
    )


def issues_filed(count: int, tracker: str | None) -> tuple[str, str | None]:
    return f"{counted(count, 'issue')} filed", tracker


def issues_not_filed(
    titles: Sequence[str], tracker: str | None
) -> tuple[str, str | None]:
    first = titles[0] if titles else None
    if first and len(titles) > 1:
        first += f" and {len(titles) - 1:,} more"
    return f"{counted(len(titles), 'issue')} not filed", _join([tracker, first])
