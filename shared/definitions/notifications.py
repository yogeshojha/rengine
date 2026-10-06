"""Notification templates: one interrupt per event."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from shared.definitions.bounty_programs import BountyEvent, event_spec
from shared.definitions.stage_counts import HTTP_SERVICE_NOUN
from shared.definitions.stage_counts import noun as _noun
from shared.definitions.surface import SURFACE_NOUN, SurfaceDimension
from shared.definitions.threat_intel import ExploitSignal
from shared.definitions.tripwires import FIRE_ON_VERB
from shared.definitions.tripwires import SAMPLE_ROWS as TRIPWIRE_SAMPLE_ROWS
from shared.definitions.vulnerabilities import (
    SEVERITY_LABELS,
    SEVERITY_ORDER,
    Severity,
)
from shared.enums.notification import NotificationSeverity, NotificationType


def _count(n: int, singular: str, plural: str) -> str:
    return f"{n:,} {singular if n == 1 else plural}"


def _more(total: int, shown: int) -> list[str]:
    return [f"and {total - shown:,} more"] if total > shown else []


ENRICHMENT_FAILED = "The lookup did not complete. Check the worker log."


def _scan_meta(scan_id: str, tab: str | None = None) -> dict:
    url = f"/scans/{scan_id}" + (f"?tab={tab}" if tab else "")
    return {"scan_id": str(scan_id), "url": url}


_SCAN_COUNT_LABELS: dict[str, tuple[str, str]] = {
    "subdomains_found": _noun(SurfaceDimension.WEB_ASSETS),
    "ips_found": _noun(SurfaceDimension.IPS),
    "open_ports_found": _noun(SurfaceDimension.SERVICES),
    "http_assets_found": HTTP_SERVICE_NOUN,
    "vulnerabilities_found": _noun(SurfaceDimension.VULNERABILITIES),
    "endpoints_found": _noun(SurfaceDimension.ENDPOINTS),
    "secrets_found": _noun(SurfaceDimension.SECRETS),
}


SCAN_COUNT_COLUMNS: tuple[str, ...] = tuple(_SCAN_COUNT_LABELS)


@dataclass(frozen=True)
class ScanDeltas:
    baseline: bool = False
    new_hosts: int = 0
    new_services: int = 0
    sensitive_services: int = 0
    new_vulnerabilities: int = 0
    vulnerability_counts: dict[str, int] = field(default_factory=dict)
    kev: int = 0
    new_secrets: int = 0
    exposures: int = 0
    dropped_hosts: int = 0
    posture_regressions: int = 0

    @property
    def critical(self) -> int:
        return self.vulnerability_counts.get(Severity.CRITICAL.value, 0)

    @property
    def high(self) -> int:
        return self.vulnerability_counts.get(Severity.HIGH.value, 0)

    def worth_reporting(self, counts: dict) -> bool:
        if not self.baseline:
            return any(counts.get(col) for col in _SCAN_COUNT_LABELS)
        return bool(
            self.new_hosts
            or self.new_services
            or self.new_vulnerabilities
            or self.new_secrets
            or self.exposures
            or self.dropped_hosts
            or self.posture_regressions
        )


_FINDING = _noun(SurfaceDimension.VULNERABILITIES)
_WEB_ASSET = _noun(SurfaceDimension.WEB_ASSETS)


def _severity_phrase(counts: dict) -> str:
    return ", ".join(
        f"{counts[name]:,} {SEVERITY_LABELS[name].lower()}"
        for name in SEVERITY_ORDER
        if counts.get(name)
    )


@dataclass(frozen=True)
class _Lead:
    key: str
    title: str
    severity: NotificationSeverity
    tab: str | None


_FINDING_LEADS = frozenset({"critical", "kev", "high", "findings"})
_ADMIN_PORT = (
    "administrative or datastore port open",
    "administrative or datastore ports open",
)
_INVENTORY: tuple[str, ...] = (
    "subdomains_found",
    "ips_found",
    "open_ports_found",
    "endpoints_found",
)


def _findings_total(d: ScanDeltas) -> int:
    return d.new_vulnerabilities if d.baseline else sum(d.vulnerability_counts.values())


def _lead(target: str, d: ScanDeltas) -> _Lead:
    vuln = SurfaceDimension.VULNERABILITIES
    err, warn, info = (
        NotificationSeverity.ERROR,
        NotificationSeverity.WARNING,
        NotificationSeverity.INFO,
    )
    finding = _noun(vuln, before="new") if d.baseline else _FINDING
    ladder = (
        (
            "critical",
            d.critical,
            _noun(vuln, before="critical"),
            err,
            "vulnerabilities",
        ),
        (
            "kev",
            d.kev,
            ("known exploited vulnerability", "known exploited vulnerabilities"),
            err,
            "vulnerabilities",
        ),
        (
            "secrets",
            d.new_secrets,
            ("exposed secret", "exposed secrets"),
            warn,
            "secrets",
        ),
        ("high", d.high, _noun(vuln, before="high"), warn, "vulnerabilities"),
        ("sensitive", d.sensitive_services, _ADMIN_PORT, warn, "services"),
        ("posture", d.posture_regressions, None, warn, None),
        ("findings", _findings_total(d), finding, info, "vulnerabilities"),
        (
            "hosts",
            d.new_hosts if d.baseline else 0,
            _noun(SurfaceDimension.WEB_ASSETS, before="new"),
            info,
            "web-assets",
        ),
        (
            "services",
            d.new_services if d.baseline else 0,
            _noun(SurfaceDimension.SERVICES, before="new"),
            info,
            "services",
        ),
        (
            "exposures",
            d.exposures,
            ("new exposure", "new exposures")
            if d.baseline
            else ("exposure", "exposures"),
            info,
            "interesting",
        ),
        ("partial", d.dropped_hosts, None, warn, "vulnerabilities"),
    )
    for key, n, noun, severity, tab in ladder:
        if not n:
            continue
        if key == "posture":
            title = f"SPF or DMARC weakened on {target}"
        elif key == "partial":
            title = f"Partial coverage on {target}"
        else:
            title = f"{_count(n, *noun)} on {target}"
        return _Lead(key, title, severity, tab)
    return _Lead("completed", f"Scan completed on {target}", info, None)


def _findings_line(total: int, counts: dict, *, new: bool) -> str:
    noun = _noun(SurfaceDimension.VULNERABILITIES, before="new") if new else _FINDING
    detail = _severity_phrase(counts)
    return _count(total, *noun) + (f" · {detail}" if detail else "")


def _inventory(counts: dict) -> str:
    return " · ".join(
        _count(n, *_SCAN_COUNT_LABELS[col])
        for col in _INVENTORY
        if (n := counts.get(col, 0))
    )


def _digest_body(counts: dict, d: ScanDeltas, lead: str) -> str:
    """Line 1 is what the list shows. Risk first, the inventory last."""
    lines: list[tuple[str, str]] = []
    total = _findings_total(d)
    if total and lead == "findings":
        lines.append(("severities", _severity_phrase(d.vulnerability_counts)))
    elif total:
        lines.append(
            ("findings", _findings_line(total, d.vulnerability_counts, new=d.baseline))
        )
    if d.kev:
        lines.append(("kev", f"{d.kev:,} known exploited"))
    if d.new_secrets:
        lines.append(
            ("secrets", _count(d.new_secrets, "exposed secret", "exposed secrets"))
        )
    if d.sensitive_services:
        lines.append(("sensitive", _count(d.sensitive_services, *_ADMIN_PORT)))
    if d.posture_regressions:
        zones = _count(d.posture_regressions, "zone", "zones")
        lines.append(("posture", f"SPF or DMARC weakened on {zones}"))
    if d.baseline:
        grown = [
            _count(n, *noun)
            for key, n, noun in (
                (
                    "hosts",
                    d.new_hosts,
                    _noun(SurfaceDimension.WEB_ASSETS, before="new"),
                ),
                (
                    "services",
                    d.new_services,
                    _noun(SurfaceDimension.SERVICES, before="new"),
                ),
            )
            if n and key != lead
        ]
        if grown:
            lines.append(("grown", " · ".join(grown)))
    if d.exposures:
        flagged = ("new asset", "new assets") if d.baseline else ("asset", "assets")
        lines.append(
            ("exposures", f"{_count(d.exposures, *flagged)} flagged as exposures")
        )
    if d.dropped_hosts:
        lines.append(
            ("coverage", f"{_count(d.dropped_hosts, *_WEB_ASSET)} not fully tested")
        )
    if not d.baseline:
        lines.append(("inventory", _inventory(counts)))
    return "\n".join(text for key, text in lines if key != lead and text)


def scan_digest(
    scan_id: str, target: str, counts: dict, deltas: ScanDeltas
) -> dict | None:
    """One message per run. The title's lead fact sets the severity."""
    if not deltas.worth_reporting(counts):
        return None
    lead = _lead(target, deltas)
    return {
        "type": NotificationType.VULNERABILITY
        if lead.key in _FINDING_LEADS
        else NotificationType.SCAN,
        "severity": lead.severity,
        "title": lead.title,
        "message": _digest_body(counts, deltas, lead.key),
        "metadata": _scan_meta(scan_id, lead.tab),
    }


def scan_failed(
    scan_id: str,
    target: str,
    engine: str,
    error: str,
    ntype: NotificationType = NotificationType.SCAN,
) -> dict:
    return {
        "type": ntype,
        "severity": NotificationSeverity.ERROR,
        "title": f"Scan failed on {target}",
        "message": f"{engine} · {error[:300]}",
        "metadata": _scan_meta(scan_id),
    }


def schedule_not_started(name: str, failed: int, total: int) -> dict:
    return {
        "type": NotificationType.SCAN,
        "severity": NotificationSeverity.ERROR,
        "title": f"Scheduled scan not started · {name}",
        "message": f"{failed:,} of {_count(total, 'target', 'targets')} not started. "
        "Check the schedule and the worker log.",
        "metadata": {"url": "/automation/schedules"},
    }


@dataclass
class IntelShift:
    """A finding whose exploitation intelligence moved without a new scan."""

    cve: str
    target: str
    finding: str
    kind: str
    scan_id: str
    vulnerability_id: str = ""


_KNOWN_EXPLOITED = frozenset({ExploitSignal.KEV.value, ExploitSignal.RANSOM_PATH.value})


def distinct_findings(shifts: list["IntelShift"]) -> list["IntelShift"]:
    seen: set[str] = set()
    out: list[IntelShift] = []
    for s in shifts:
        if s.vulnerability_id and s.vulnerability_id in seen:
            continue
        seen.add(s.vulnerability_id)
        out.append(s)
    return out


def intel_changed(shifts: list["IntelShift"], shown: int = 5) -> dict | None:
    """Findings that gained an exploitation signal since the last refresh."""
    if not shifts:
        return None
    exploited = any(s.kind in _KNOWN_EXPLOITED for s in shifts)
    shifts = distinct_findings(shifts)
    head = _count(len(shifts), *_FINDING)
    lines = [f"{s.cve} · {s.target} · {s.finding}" for s in shifts[:shown]]
    query = "is%3Aexploitable" if exploited else "is%3Aweaponised"
    return {
        "type": NotificationType.SCAN,
        "severity": NotificationSeverity.ERROR
        if exploited
        else NotificationSeverity.WARNING,
        "title": f"{head} now known exploited"
        if exploited
        else f"Public exploit available for {head}",
        "message": "\n".join(lines + _more(len(shifts), shown)),
        "metadata": {"url": f"/surface/vulnerabilities?vuln_q={query}"},
    }


@dataclass(frozen=True)
class SoftwareExposure:
    """A software CVE match the nightly corpus refresh wrote for the first time."""

    cve: str
    host: str
    name: str
    version: str
    severity: str
    is_kev: bool
    kev_ransomware: bool


def software_exposed(
    exposures: list["SoftwareExposure"], shown: int = 5
) -> dict | None:
    """Known exploited CVEs that newly match a detected software version."""
    loud: list[SoftwareExposure] = []
    seen: set[tuple[str, str, str, str]] = set()
    for e in exposures:
        key = (e.cve, e.host, e.name, e.version)
        if key in seen or not e.is_kev:
            continue
        seen.add(key)
        loud.append(e)
    if not loud:
        return None
    cves = sorted({e.cve for e in loud})
    assets = _count(len({e.host for e in loud}), "asset", "assets")
    subject = (
        cves[0]
        if len(cves) == 1
        else _count(len(cves), "known exploited CVE", "known exploited CVEs")
    )
    lines = [f"{e.cve} · {e.host} · {e.name} {e.version}" for e in loud[:shown]]
    url = (
        f"/surface/cve/{cves[0]}"
        if len(cves) == 1
        else "/surface/software?sw_q=is%3Akev%20seen%3A%3C24h"
    )
    return {
        "type": NotificationType.VULNERABILITY,
        "severity": NotificationSeverity.ERROR,
        "title": f"{subject} matched on {assets}",
        "message": "\n".join(lines + _more(len(loud), shown)),
        "metadata": {"url": url},
    }


@dataclass
class BountyChange:
    kind: str
    program: str
    handle: str
    asset: str | None = None


_BOUNTY_HEADS: dict[str, tuple[str, str]] = {
    BountyEvent.WENT_OUT_OF_SCOPE.value: ("asset out of scope", "assets out of scope"),
    BountyEvent.SCOPE_ADDED.value: ("scope addition", "scope additions"),
    BountyEvent.CAME_INTO_SCOPE.value: ("asset back in scope", "assets back in scope"),
    BountyEvent.SUBMISSIONS_OPENED.value: (
        "program accepting reports",
        "programs accepting reports",
    ),
    BountyEvent.BOUNTIES_STARTED.value: (
        "program now paying bounties",
        "programs now paying bounties",
    ),
    BountyEvent.PROGRAM_ADDED.value: ("new program", "new programs"),
}


def _bounty_line(change: "BountyChange") -> str:
    what = f" · {change.asset}" if change.asset else ""
    return f"{event_spec(change.kind).label} · {change.program}{what}"


def _bounty_title(by_kind: dict[str, int]) -> str:
    total = sum(by_kind.values())
    stop = by_kind.get(BountyEvent.WENT_OUT_OF_SCOPE.value, 0)
    if stop:
        head = _count(stop, *_BOUNTY_HEADS[BountyEvent.WENT_OUT_OF_SCOPE.value])
        rest = total - stop
        return head + (
            f", {_count(rest, 'other update', 'other updates')}" if rest else ""
        )
    if len(by_kind) == 1:
        kind = next(iter(by_kind))
        if kind in _BOUNTY_HEADS:
            return _count(total, *_BOUNTY_HEADS[kind])
    return _count(total, "program update", "program updates")


def bounty_changes(
    changes: list["BountyChange"],
    shown: int = 6,
    counts: dict[str, int] | None = None,
) -> dict | None:
    """What followed programs changed since the last sync."""
    if not changes:
        return None
    by_kind = {k: n for k, n in (counts or {}).items() if n}
    if not by_kind:
        for c in changes:
            by_kind[c.kind] = by_kind.get(c.kind, 0) + 1
    stop = BountyEvent.WENT_OUT_OF_SCOPE.value
    ordered = sorted(changes, key=lambda c: c.kind != stop)
    lines = [_bounty_line(c) for c in ordered[:shown]]
    return {
        "type": NotificationType.INTEGRATION,
        "severity": NotificationSeverity.WARNING
        if by_kind.get(stop)
        else NotificationSeverity.INFO,
        "title": _bounty_title(by_kind),
        "message": "\n".join(lines + _more(sum(by_kind.values()), len(lines))),
        "metadata": {"url": "/bounty-hub?tab=updates"},
    }


@dataclass(frozen=True)
class WatchAlert:
    program: str
    host: str
    matched_item: str | None
    status_code: int | None
    title: str | None
    tech: tuple[str, ...]
    ips: tuple[str, ...]
    issuer: str | None
    not_before: datetime | None
    scan_id: str | None
    target_id: str | None = None
    wildcard: bool = False
    repeat: bool = False


def watch_alert(alert: WatchAlert) -> dict:
    """One message per new in-scope host, again when the host changes."""
    head = "Changed in-scope asset" if alert.repeat else "New in-scope asset"
    lines = [alert.host]
    if alert.status_code is not None:
        lines.append(
            str(alert.status_code) + (f" · {alert.title}" if alert.title else "")
        )
    if alert.tech:
        lines.append(", ".join(alert.tech[:6]))
    if alert.ips:
        lines.append(
            ", ".join(alert.ips[:4]) + (" · wildcard DNS" if alert.wildcard else "")
        )
    if alert.issuer or alert.not_before:
        when = alert.not_before.strftime("%Y-%m-%d %H:%M") if alert.not_before else ""
        lines.append(
            "Certificate " + " · ".join(p for p in (alert.issuer or "", when) if p)
        )
    if alert.matched_item:
        lines.append(f"Scope {alert.matched_item}")
    return {
        "type": NotificationType.WATCH,
        "severity": NotificationSeverity.INFO,
        "title": f"{head} · {alert.program}",
        "message": "\n".join(lines),
        "metadata": _scan_meta(alert.scan_id)
        if alert.scan_id
        else {"target_id": alert.target_id, "url": f"/targets/{alert.target_id}"}
        if alert.target_id
        else {},
    }


def _worst_severity(by_severity: dict[str, int]) -> NotificationSeverity:
    if by_severity.get(Severity.CRITICAL.value):
        return NotificationSeverity.ERROR
    if by_severity.get(Severity.HIGH.value):
        return NotificationSeverity.WARNING
    return NotificationSeverity.INFO


@dataclass
class NewChecksResult:
    scan_id: str
    target: str
    checks: int
    findings: int
    by_severity: dict[str, int] = field(default_factory=dict)


def new_checks_result(result: NewChecksResult) -> dict | None:
    """One message per follow-up run that found something."""
    if result.findings <= 0:
        return None
    return {
        "type": NotificationType.NEW_CHECKS,
        "severity": _worst_severity(result.by_severity),
        "title": f"New checks found {_count(result.findings, *_FINDING)} on {result.target}",
        "message": "\n".join(
            (
                _findings_line(result.findings, result.by_severity, new=False),
                f"{_count(result.checks, 'new check', 'new checks')} tested",
            )
        ),
        "metadata": _scan_meta(result.scan_id, "vulnerabilities"),
    }


@dataclass(frozen=True)
class FiredRowLike:
    label: str
    detail: str = ""
    severity: str | None = None


@dataclass
class TripwireFired:
    name: str
    target: str
    dimension: str
    fire_on: str
    fired: int
    rows: Sequence[FiredRowLike]
    run_id: str
    scan_id: str
    live: bool = False
    rescan: "TripwireRescan | None" = None


@dataclass
class TripwireRescan:
    completed: bool
    by_severity: dict[str, int] = field(default_factory=dict)


def _row_severity(rows: Sequence[FiredRowLike]) -> NotificationSeverity:
    found: dict[str, int] = {}
    for r in rows:
        if r.severity:
            found[r.severity] = found.get(r.severity, 0) + 1
    return _worst_severity(found)


def _louder(a: NotificationSeverity, b: NotificationSeverity) -> NotificationSeverity:
    order = (
        NotificationSeverity.INFO,
        NotificationSeverity.WARNING,
        NotificationSeverity.ERROR,
    )
    return a if order.index(a) >= order.index(b) else b


def _rescan_line(rescan: TripwireRescan) -> str:
    if not rescan.completed:
        return "Rescan did not complete"
    total = sum(rescan.by_severity.values())
    if not total:
        return "Rescan · no findings"
    return "Rescan · " + _findings_line(total, rescan.by_severity, new=False)


def tripwire_fired(event: TripwireFired) -> dict:
    """One message per tripwire per run, with the rescan result when one ran."""
    singular, plural = SURFACE_NOUN[event.dimension]
    head = f"{_count(event.fired, singular, plural)} {FIRE_ON_VERB[event.fire_on]}"
    lines = [
        f"{head} on {event.target}" + (" · scan in progress" if event.live else "")
    ]
    shown = list(event.rows[:TRIPWIRE_SAMPLE_ROWS])
    lines += [r.label + (f" · {r.detail}" if r.detail else "") for r in shown]
    lines += _more(event.fired, len(shown))
    severity = _row_severity(event.rows)
    if event.rescan is not None:
        lines.append(_rescan_line(event.rescan))
        severity = _louder(severity, _worst_severity(event.rescan.by_severity))
    return {
        "type": NotificationType.TRIPWIRE,
        "severity": severity,
        "title": f"Tripwire · {event.name}",
        "message": "\n".join(lines),
        "metadata": {"scan_id": event.scan_id, "url": f"/tripwires?run={event.run_id}"},
    }


@dataclass
class TripwireRunResult:
    name: str
    target: str
    findings: int
    by_severity: dict[str, int] = field(default_factory=dict)
    scan_id: str = ""


def tripwire_run_result(result: TripwireRunResult) -> dict | None:
    """A rescan with no notify action speaks only when it found something."""
    if result.findings <= 0:
        return None
    return {
        "type": NotificationType.TRIPWIRE,
        "severity": _worst_severity(result.by_severity),
        "title": f"Tripwire · {result.name}",
        "message": f"Rescan of {result.target} · "
        + _findings_line(result.findings, result.by_severity, new=False),
        "metadata": _scan_meta(result.scan_id, "vulnerabilities"),
    }
