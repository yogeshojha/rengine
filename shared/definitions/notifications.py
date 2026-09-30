"""Notification templates: one interrupt per event."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from shared.definitions.bounty_programs import BountyEvent, event_spec
from shared.definitions.interest import InterestBand, kind_label
from shared.definitions.surface import SURFACE_NOUN, SurfaceDimension
from shared.definitions.tripwires import FIRE_ON_VERB
from shared.definitions.tripwires import SAMPLE_ROWS as TRIPWIRE_SAMPLE_ROWS
from shared.definitions.vulnerabilities import (
    ALERT_SEVERITIES,
    SEVERITY_LABELS,
    SEVERITY_ORDER,
    Severity,
)
from shared.enums.notification import NotificationSeverity, NotificationType


def _count(n: int, singular: str, plural: str) -> str:
    return f"{n:,} {singular if n == 1 else plural}"


MAX_NAMED_TARGETS = 3
ENRICHMENT_FAILED = "The lookup did not complete. Check the worker log."


def _subject(names: Sequence[str], failed: int, total: int) -> str:
    """Name the targets when there are few enough to read, else count them."""
    listed = [n for n in names if n][:MAX_NAMED_TARGETS]
    if listed and failed <= MAX_NAMED_TARGETS:
        return ", ".join(listed)
    return f"{failed} of {total} {'target' if total == 1 else 'targets'}"


def whois_enrichment_incomplete(
    success: int, failed: int, total: int, names: Sequence[str] = ()
) -> dict | None:
    if not failed:
        return None
    return {
        "type": NotificationType.TARGET,
        "severity": NotificationSeverity.WARNING,
        "title": "WHOIS lookup failed",
        "message": (
            f"WHOIS lookup failed for {_subject(names, failed, total)}."
            f"{f' {success} succeeded.' if success else ''}"
        ),
    }


def whois_enrichment_failed() -> dict:
    return {
        "type": NotificationType.TARGET,
        "severity": NotificationSeverity.ERROR,
        "title": "WHOIS enrichment failed",
        "message": "No target was enriched. Check the worker log.",
    }


def ripestat_enrichment_incomplete(
    success: int, failed: int, skipped: int, total: int, names: Sequence[str] = ()
) -> dict | None:
    if not failed:
        return None
    return {
        "type": NotificationType.TARGET,
        "severity": NotificationSeverity.WARNING,
        "title": "BGP enrichment failed",
        "message": (
            f"BGP lookup failed for {_subject(names, failed, total)}."
            f"{f' {success} succeeded.' if success else ''}"
            f"{f' {skipped} had nothing to look up.' if skipped else ''}"
        ),
    }


def ripestat_enrichment_failed() -> dict:
    return {
        "type": NotificationType.TARGET,
        "severity": NotificationSeverity.ERROR,
        "title": "BGP enrichment failed",
        "message": "No target was enriched. Check the worker log.",
    }


def _scan_meta(scan_id: str, tab: str | None = None) -> dict:
    url = f"/scans/{scan_id}" + (f"?tab={tab}" if tab else "")
    return {"scan_id": str(scan_id), "url": url}


def _noun(
    dimension: SurfaceDimension, *, before: str = "", after: str = ""
) -> tuple[str, str]:
    singular, plural = SURFACE_NOUN[dimension.value]
    return (
        " ".join(w for w in (before, singular, after) if w),
        " ".join(w for w in (before, plural, after) if w),
    )


HTTP_SERVICE_NOUN = ("HTTP service", "HTTP services")


_SCAN_COUNT_LABELS: dict[str, tuple[str, str]] = {
    "subdomains_found": _noun(SurfaceDimension.WEB_ASSETS),
    "ips_found": _noun(SurfaceDimension.IPS),
    "open_ports_found": _noun(SurfaceDimension.SERVICES),
    "http_assets_found": HTTP_SERVICE_NOUN,
    "vulnerabilities_found": _noun(SurfaceDimension.VULNERABILITIES),
    "endpoints_found": _noun(SurfaceDimension.ENDPOINTS),
    "secrets_found": _noun(SurfaceDimension.SECRETS),
}


def scan_count_summary(counts: dict) -> str:
    parts = [
        _count(n, singular, plural)
        for col, (singular, plural) in _SCAN_COUNT_LABELS.items()
        if (n := counts.get(col, 0))
    ]
    return ", ".join(parts) if parts else "no results"


_STAGE_COUNT_LABELS: dict[str, tuple[str, str]] = {
    "active": _noun(SurfaceDimension.WEB_ASSETS, before="resolving"),
    "addresses": _noun(SurfaceDimension.IPS),
    "alive": _noun(SurfaceDimension.WEB_ASSETS, before="responsive"),
    "answered": ("answered", "answered"),
    "bgp": ("BGP record", "BGP records"),
    "cdn": ("CDN-fronted address", "CDN-fronted addresses"),
    "checked": _noun(SurfaceDimension.SERVICES, after="checked"),
    "checks": ("check run", "checks run"),
    "cloud": ("cloud-hosted address", "cloud-hosted addresses"),
    "dns_records": ("DNS record", "DNS records"),
    "edge_only": ("CDN edge address", "CDN edge addresses"),
    "endpoints": _noun(SurfaceDimension.ENDPOINTS),
    "endpoints_new": _noun(SurfaceDimension.ENDPOINTS, before="new"),
    "endpoints_probed": _noun(SurfaceDimension.ENDPOINTS, after="requested"),
    "enriched": _noun(SurfaceDimension.IPS, after="enriched"),
    "fingerprinted": _noun(SurfaceDimension.SERVICES, after="identified"),
    "http_assets": HTTP_SERVICE_NOUN,
    "ips": _noun(SurfaceDimension.IPS),
    "known_ports": _noun(SurfaceDimension.SERVICES, before="known"),
    "new": ("new", "new"),
    "open_ports": _noun(SurfaceDimension.SERVICES, before="open"),
    "posture_issues": ("posture check failing", "posture checks failing"),
    "probed": _noun(SurfaceDimension.WEB_ASSETS, after="probed"),
    "ptr": ("PTR record", "PTR records"),
    "scanned": _noun(SurfaceDimension.IPS, after="scanned"),
    "screenshots": ("screenshot", "screenshots"),
    "secrets": _noun(SurfaceDimension.SECRETS),
    "documents": ("response read", "responses read"),
    "skipped": ("skipped", "skipped"),
    "subdomains": _noun(SurfaceDimension.WEB_ASSETS),
    "targets": ("target", "targets"),
    "vulnerabilities": _noun(SurfaceDimension.VULNERABILITIES),
    "waf": ("firewall identified", "firewalls identified"),
    "web_services": _noun(SurfaceDimension.SERVICES, before="web"),
    "whois": ("WHOIS record", "WHOIS records"),
    "zones": ("zone checked", "zones checked"),
}


def stage_count_summary(counts: dict) -> str:
    """Label every figure a stage reports."""
    parts = [
        _count(n, *_STAGE_COUNT_LABELS[key])
        for key, n in counts.items()
        if isinstance(n, int) and n and key in _STAGE_COUNT_LABELS
    ]
    return ", ".join(parts) if parts else "no results"


@dataclass(frozen=True)
class ScanDeltas:
    baseline: bool = False
    new_hosts: int = 0
    new_services: int = 0
    sensitive_services: int = 0
    new_vulnerabilities: int = 0
    vulnerability_counts: dict[str, int] = field(default_factory=dict)
    kev: int = 0
    dropped_hosts: int = 0
    posture_regressions: int = 0

    @property
    def critical(self) -> int:
        return self.vulnerability_counts.get(Severity.CRITICAL.value, 0)

    @property
    def severe(self) -> int:
        return sum(self.vulnerability_counts.get(s, 0) for s in ALERT_SEVERITIES)

    def worth_reporting(self, counts: dict) -> bool:
        if not self.baseline:
            return any(counts.get(col) for col in _SCAN_COUNT_LABELS)
        return bool(
            self.new_hosts
            or self.new_services
            or self.new_vulnerabilities
            or self.dropped_hosts
            or self.posture_regressions
        )


def _severity_phrase(counts: dict) -> str:
    return ", ".join(
        f"{counts[name]} {SEVERITY_LABELS[name].lower()}"
        for name in SEVERITY_ORDER
        if counts.get(name)
    )


def _digest_title(target: str, deltas: ScanDeltas) -> str:
    if deltas.critical:
        head = _count(
            deltas.critical, *_noun(SurfaceDimension.VULNERABILITIES, before="critical")
        )
    elif deltas.kev:
        head = _count(
            deltas.kev, "exploited vulnerability", "exploited vulnerabilities"
        )
    elif deltas.severe or deltas.sensitive_services:
        head = "New exposure"
    elif not deltas.baseline:
        return f"First scan of {target}"
    elif deltas.new_vulnerabilities:
        head = _count(
            deltas.new_vulnerabilities,
            *_noun(SurfaceDimension.VULNERABILITIES, before="new"),
        )
    elif deltas.posture_regressions:
        head = "Sender policy weakened"
    elif deltas.new_hosts or deltas.new_services:
        head = "New assets"
    else:
        head = "Partial coverage"
    return f"{head} on {target}"


def _digest_body(counts: dict, deltas: ScanDeltas) -> str:
    if not deltas.baseline:
        body = f"No earlier run. This run found {scan_count_summary(counts)}."
    else:
        detail = _severity_phrase(deltas.vulnerability_counts)
        parts = [
            text
            for text, n in (
                (
                    _count(
                        deltas.new_hosts,
                        *_noun(SurfaceDimension.WEB_ASSETS, before="new"),
                    ),
                    deltas.new_hosts,
                ),
                (
                    _count(
                        deltas.new_services,
                        *_noun(SurfaceDimension.SERVICES, before="new"),
                    ),
                    deltas.new_services,
                ),
                (
                    _count(
                        deltas.new_vulnerabilities,
                        *_noun(SurfaceDimension.VULNERABILITIES, before="new"),
                    )
                    + (f" · {detail}" if detail else ""),
                    deltas.new_vulnerabilities,
                ),
            )
            if n
        ]
        if parts:
            body = ", ".join(parts) + "."
        else:
            body = "Nothing new since the previous run."

    if deltas.sensitive_services:
        n = deltas.sensitive_services
        body += (
            f" {n} {'is' if n == 1 else 'are'} on an administrative or datastore port."
        )
    if deltas.kev:
        body += (
            f" {deltas.kev} {'is' if deltas.kev == 1 else 'are'} "
            f"known to be exploited in the wild."
        )
    if deltas.posture_regressions:
        body += (
            f" {_count(deltas.posture_regressions, 'zone', 'zones')} lost SPF or "
            "DMARC protection since the previous run."
        )
    if deltas.dropped_hosts:
        body += (
            " Testing stopped on "
            f"{_count(deltas.dropped_hosts, *_noun(SurfaceDimension.WEB_ASSETS))}."
        )
    return body


def scan_digest(
    scan_id: str, target: str, counts: dict, deltas: ScanDeltas
) -> dict | None:
    """One row per run."""
    if not deltas.worth_reporting(counts):
        return None

    if deltas.critical or deltas.kev:
        severity = NotificationSeverity.ERROR
    elif (
        deltas.severe
        or deltas.sensitive_services
        or deltas.dropped_hosts
        or deltas.posture_regressions
    ):
        severity = NotificationSeverity.WARNING
    else:
        severity = NotificationSeverity.SUCCESS

    if deltas.new_vulnerabilities or deltas.dropped_hosts:
        tab = "vulnerabilities"
    elif deltas.sensitive_services or deltas.new_services:
        tab = "services"
    else:
        tab = None

    return {
        "type": NotificationType.VULNERABILITY
        if deltas.new_vulnerabilities
        else NotificationType.SCAN,
        "severity": severity,
        "title": _digest_title(target, deltas),
        "message": _digest_body(counts, deltas),
        "metadata": _scan_meta(scan_id, tab),
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
        "message": f"The {engine} run did not finish: {error[:300]}",
        "metadata": _scan_meta(scan_id),
    }


@dataclass
class InterestLead:
    host: str
    band: str
    score: int
    kinds: tuple[str, ...] = ()
    source: str = ""


def _lead_line(lead: InterestLead) -> str:
    reasons = ", ".join(kind_label(k) for k in lead.kinds[:3])
    return f"• {lead.host}" + (f" · {reasons}" if reasons else "")


def scan_interesting(
    scan_id: str, target: str, leads: list[InterestLead], shown: int = 5
) -> dict | None:
    """Hosts not flagged by an earlier scan of this target."""
    if not leads:
        return None
    critical = [x for x in leads if x.band == InterestBand.CRITICAL.value]
    severity = NotificationSeverity.WARNING if critical else NotificationSeverity.INFO
    head = _count(len(leads), "new asset", "new assets")
    noun = "an exposure" if len(leads) == 1 else "exposures"
    title = f"{head} flagged as {noun} on {target}"
    body = "\n".join(_lead_line(lead) for lead in leads[:shown])
    if len(leads) > shown:
        body += f"\n… and {len(leads) - shown} more"
    return {
        "type": NotificationType.SCAN,
        "severity": severity,
        "title": title,
        "message": body,
        "metadata": _scan_meta(scan_id, "interesting"),
    }


@dataclass
class IntelShift:
    """A finding whose exploitation intelligence moved without a new scan."""

    cve: str
    target: str
    finding: str
    kind: str
    scan_id: str


def _shift_line(shift: IntelShift) -> str:
    return f"• {shift.cve} · {shift.target} · {shift.finding}"


def intel_changed(shifts: list["IntelShift"], shown: int = 5) -> dict | None:
    """Delta-only: findings that earned a new exploitation signal since the last refresh."""
    if not shifts:
        return None
    exploited = [s for s in shifts if s.kind in {"kev", "ransom_path", "fresh_exploit"}]
    severity = NotificationSeverity.ERROR if exploited else NotificationSeverity.WARNING
    head = _count(len(shifts), "finding", "findings")
    what = "became known-exploited" if exploited else "gained a public exploit"
    title = f"{head} {what} since the last refresh"
    body = "\n".join(_shift_line(s) for s in shifts[:shown])
    if len(shifts) > shown:
        body += f"\n… and {len(shifts) - shown} more"
    query = "is%3Aexploitable" if exploited else "is%3Aweaponised"
    return {
        "type": NotificationType.SCAN,
        "severity": severity,
        "title": title,
        "message": body,
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


def _exposure_line(e: SoftwareExposure) -> str:
    return f"• {e.cve} · {e.host} · {e.name} {e.version}"


def software_exposed(
    exposures: list["SoftwareExposure"], shown: int = 5
) -> dict | None:
    """Delta-only: matches absent from the previous corpus. Severe or known exploited."""
    loud: list[SoftwareExposure] = []
    seen: set[tuple[str, str, str, str]] = set()
    for e in exposures:
        key = (e.cve, e.host, e.name, e.version)
        if key in seen or not (e.is_kev or e.severity in ALERT_SEVERITIES):
            continue
        seen.add(key)
        loud.append(e)
    if not loud:
        return None
    exploited = any(e.is_kev for e in loud)
    cves = sorted({e.cve for e in loud})
    kev_cves = {e.cve for e in loud if e.is_kev}
    hosts = len({e.host for e in loud})
    assets = _count(hosts, "asset", "assets")
    verb = "matches" if hosts == 1 else "match"
    if kev_cves == set(cves):
        what = "known-exploited "
    elif not kev_cves:
        what = "published "
    else:
        what = ""
    if len(cves) == 1:
        title = f"{assets} newly {verb} {cves[0]}"
    else:
        title = (
            f"{assets} newly {verb} {_count(len(cves), f'{what}CVE', f'{what}CVEs')}"
        )
    body = "\n".join(_exposure_line(e) for e in loud[:shown])
    if len(loud) > shown:
        body += f"\n… and {len(loud) - shown} more"
    url = (
        f"/surface/cve/{cves[0]}"
        if len(cves) == 1
        else "/surface/software?sw_q=seen%3A%3C24h"
    )
    return {
        "type": NotificationType.VULNERABILITY,
        "severity": NotificationSeverity.ERROR
        if exploited
        else NotificationSeverity.WARNING,
        "title": title,
        "message": body,
        "metadata": {"url": url},
    }


@dataclass
class BountyChange:
    kind: str
    program: str
    handle: str
    asset: str | None = None


def _bounty_line(change: "BountyChange") -> str:
    what = f" · {change.asset}" if change.asset else ""
    return f"• {event_spec(change.kind).label} · {change.program}{what}"


def bounty_changes(
    changes: list["BountyChange"],
    shown: int = 6,
    counts: dict[str, int] | None = None,
) -> dict | None:
    """Delta-only: what a program changed since the last sync."""
    if not changes:
        return None
    by_kind = counts or {}
    if not by_kind:
        for c in changes:
            by_kind[c.kind] = by_kind.get(c.kind, 0) + 1
    total = sum(by_kind.values())
    stop = by_kind.get(BountyEvent.WENT_OUT_OF_SCOPE.value, 0)
    fresh = by_kind.get(BountyEvent.PROGRAM_ADDED.value, 0) + by_kind.get(
        BountyEvent.SCOPE_ADDED.value, 0
    )
    severity = NotificationSeverity.WARNING if stop else NotificationSeverity.INFO
    if stop:
        title = _count(stop, "asset", "assets") + " went out of scope"
    elif fresh:
        title = _count(fresh, "scope change", "scope changes")
    else:
        title = _count(total, "program change", "program changes")
    body = "\n".join(_bounty_line(c) for c in changes[:shown])
    if total > shown:
        body += f"\n… and {total - shown} more"
    return {
        "type": NotificationType.INTEGRATION,
        "severity": severity,
        "title": title,
        "message": body,
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


@dataclass
class NewChecksSweep:
    templates: int
    targets: int
    busy: int = 0
    waiting: int = 0
    skipped: int = 0


def new_checks_started(sweep: NewChecksSweep) -> dict | None:
    """One message per project when the library gained checks and follow-up runs started."""
    if sweep.templates <= 0:
        return None
    noun = "check" if sweep.templates == 1 else "checks"
    lines = [
        f"Follow-up runs started for {sweep.targets} "
        f"{'target' if sweep.targets == 1 else 'targets'}."
    ]
    if sweep.busy:
        lines.append(
            f"{sweep.busy} {'target' if sweep.busy == 1 else 'targets'} skipped: "
            "a scan is running."
        )
    if sweep.waiting:
        lines.append(
            f"{sweep.waiting} {'target waits' if sweep.waiting == 1 else 'targets wait'} "
            "for a completed scan."
        )
    if sweep.skipped:
        lines.append(
            f"{sweep.skipped} {'target' if sweep.skipped == 1 else 'targets'} had "
            "nothing to run: no applicable check, no web asset, or passive intensity."
        )
    return {
        "type": NotificationType.NEW_CHECKS,
        "severity": NotificationSeverity.INFO,
        "title": f"{sweep.templates} new {noun} in the library",
        "message": "\n".join(lines),
        "metadata": {"url": "/arsenal?tab=nuclei"},
    }


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
    counts = [
        f"{n} {sev}" for sev in SEVERITY_ORDER if (n := result.by_severity.get(sev, 0))
    ]
    checks = (
        f"{result.checks} new {'check' if result.checks == 1 else 'checks'} tested."
    )
    found = f"{result.findings} {'finding' if result.findings == 1 else 'findings'}"
    if counts:
        found += ": " + ", ".join(counts)
    severity = NotificationSeverity.INFO
    if result.by_severity.get(Severity.CRITICAL.value):
        severity = NotificationSeverity.ERROR
    elif result.by_severity.get(Severity.HIGH.value):
        severity = NotificationSeverity.WARNING
    return {
        "type": NotificationType.NEW_CHECKS,
        "severity": severity,
        "title": f"New checks · {result.target}",
        "message": f"{checks}\n{found}.",
        "metadata": _scan_meta(result.scan_id, "vulnerabilities"),
    }


def watch_alert(alert: WatchAlert) -> dict:
    """One message per new in-scope host, again only when the host changes."""
    head = "Changed in-scope asset" if alert.repeat else "New in-scope asset"
    lines = [alert.host]
    if alert.status_code is not None:
        answer = str(alert.status_code)
        if alert.title:
            answer += f" · {alert.title}"
        lines.append(answer)
    if alert.tech:
        lines.append(", ".join(alert.tech[:6]))
    if alert.ips:
        addresses = ", ".join(alert.ips[:4])
        lines.append(addresses + (" · wildcard DNS" if alert.wildcard else ""))
    if alert.issuer or alert.not_before:
        when = alert.not_before.strftime("%Y-%m-%d %H:%M") if alert.not_before else ""
        lines.append(" · ".join(p for p in (alert.issuer or "", when) if p))
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


def _worst(rows: Sequence[FiredRowLike]) -> NotificationSeverity:
    found = {r.severity for r in rows if r.severity}
    if Severity.CRITICAL.value in found:
        return NotificationSeverity.ERROR
    if Severity.HIGH.value in found:
        return NotificationSeverity.WARNING
    return NotificationSeverity.INFO


def _tripwire_meta(run_id: str, scan_id: str) -> dict:
    return {"scan_id": scan_id, "url": f"/tripwires?run={run_id}"}


def tripwire_fired(event: TripwireFired) -> dict:
    """One message per tripwire per run, listing the rows that fired."""
    singular, plural = SURFACE_NOUN[event.dimension]
    head = f"{_count(event.fired, singular, plural)} {FIRE_ON_VERB[event.fire_on]}"
    lines = [f"{head} on {event.target}" + (" · scan running" if event.live else "")]
    for row in event.rows[:TRIPWIRE_SAMPLE_ROWS]:
        lines.append(row.label + (f" · {row.detail}" if row.detail else ""))
    if event.fired > TRIPWIRE_SAMPLE_ROWS:
        lines.append(f"and {event.fired - TRIPWIRE_SAMPLE_ROWS} more")
    return {
        "type": NotificationType.TRIPWIRE,
        "severity": _worst(event.rows),
        "title": f"Tripwire · {event.name}",
        "message": "\n".join(lines),
        "metadata": _tripwire_meta(event.run_id, event.scan_id),
    }


@dataclass
class TripwireRunResult:
    name: str
    target: str
    label: str
    findings: int
    by_severity: dict[str, int] = field(default_factory=dict)
    run_id: str = ""
    scan_id: str = ""


def tripwire_run_result(result: TripwireRunResult) -> dict | None:
    """One message per focused run a tripwire started that found something."""
    if result.findings <= 0:
        return None
    counts = [
        f"{n} {sev}" for sev in SEVERITY_ORDER if (n := result.by_severity.get(sev, 0))
    ]
    found = f"{result.findings} {'finding' if result.findings == 1 else 'findings'}"
    if counts:
        found += ": " + ", ".join(counts)
    severity = NotificationSeverity.INFO
    if result.by_severity.get(Severity.CRITICAL.value):
        severity = NotificationSeverity.ERROR
    elif result.by_severity.get(Severity.HIGH.value):
        severity = NotificationSeverity.WARNING
    return {
        "type": NotificationType.TRIPWIRE,
        "severity": severity,
        "title": f"Tripwire · {result.name}",
        "message": f"{result.label} completed on {result.target}.\n{found}.",
        "metadata": _scan_meta(result.scan_id, "vulnerabilities"),
    }
