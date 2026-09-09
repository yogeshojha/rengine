"""Notification templates: one interrupt per event, never a copy of the activity log."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from shared.definitions.bounty_programs import BountyEvent, event_spec
from shared.definitions.interest import InterestBand, kind_label
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
            f"WHOIS could not be resolved for {_subject(names, failed, total)}"
            f"{f'; {success} succeeded' if success else ''}."
        ),
    }


def whois_enrichment_failed(error: str) -> dict:
    return {
        "type": NotificationType.TARGET,
        "severity": NotificationSeverity.ERROR,
        "title": "WHOIS enrichment failed",
        "message": f"WHOIS enrichment failed. {error}",
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
            f"BGP data could not be resolved for {_subject(names, failed, total)}"
            f"{f'; {success} succeeded' if success else ''}"
            f"{f', {skipped} had nothing to look up' if skipped else ''}."
        ),
    }


def ripestat_enrichment_failed(error: str) -> dict:
    return {
        "type": NotificationType.TARGET,
        "severity": NotificationSeverity.ERROR,
        "title": "BGP enrichment failed",
        "message": f"BGP enrichment failed. {error}",
    }


def _scan_meta(scan_id: str, tab: str | None = None) -> dict:
    url = f"/scans/{scan_id}" + (f"?tab={tab}" if tab else "")
    return {"scan_id": str(scan_id), "url": url}


_SCAN_COUNT_LABELS = {
    "subdomains_found": ("host", "hosts"),
    "ips_found": ("address", "addresses"),
    "open_ports_found": ("service", "services"),
    "http_assets_found": ("HTTP service", "HTTP services"),
    "vulnerabilities_found": ("finding", "findings"),
    "endpoints_found": ("endpoint", "endpoints"),
}


def scan_count_summary(counts: dict) -> str:
    parts = [
        _count(n, singular, plural)
        for col, (singular, plural) in _SCAN_COUNT_LABELS.items()
        if (n := counts.get(col, 0))
    ]
    return ", ".join(parts) if parts else "no results"


_STAGE_COUNT_LABELS: dict[str, tuple[str, str]] = {
    "active": ("resolving host", "resolving hosts"),
    "addresses": ("address", "addresses"),
    "alive": ("responsive host", "responsive hosts"),
    "answered": ("answered", "answered"),
    "bgp": ("BGP record", "BGP records"),
    "cdn": ("CDN-fronted address", "CDN-fronted addresses"),
    "checked": ("service checked", "services checked"),
    "checks": ("check run", "checks run"),
    "cloud": ("cloud-hosted address", "cloud-hosted addresses"),
    "dns_records": ("DNS record", "DNS records"),
    "edge_only": ("CDN edge address", "CDN edge addresses"),
    "endpoints": ("endpoint", "endpoints"),
    "endpoints_new": ("new endpoint", "new endpoints"),
    "endpoints_probed": ("endpoint requested", "endpoints requested"),
    "enriched": ("address enriched", "addresses enriched"),
    "fingerprinted": ("service identified", "services identified"),
    "http_assets": ("web service", "web services"),
    "ips": ("address", "addresses"),
    "known_ports": ("known service", "known services"),
    "new": ("new", "new"),
    "open_ports": ("open service", "open services"),
    "probed": ("host probed", "hosts probed"),
    "ptr": ("PTR record", "PTR records"),
    "scanned": ("address scanned", "addresses scanned"),
    "screenshots": ("screenshot", "screenshots"),
    "skipped": ("skipped", "skipped"),
    "subdomains": ("host", "hosts"),
    "targets": ("target", "targets"),
    "vulnerabilities": ("finding", "findings"),
    "waf": ("firewall identified", "firewalls identified"),
    "web_services": ("web service", "web services"),
    "whois": ("WHOIS record", "WHOIS records"),
}


def stage_count_summary(counts: dict) -> str:
    """Label every figure a stage reports. An unlabelled key is omitted, never printed raw."""
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
        )


def _severity_phrase(counts: dict) -> str:
    return ", ".join(
        f"{counts[name]} {SEVERITY_LABELS[name].lower()}"
        for name in SEVERITY_ORDER
        if counts.get(name)
    )


def _digest_title(target: str, deltas: ScanDeltas) -> str:
    if deltas.critical:
        head = _count(deltas.critical, "critical finding", "critical findings")
    elif deltas.kev:
        head = _count(
            deltas.kev, "exploited vulnerability", "exploited vulnerabilities"
        )
    elif deltas.severe or deltas.sensitive_services:
        head = "New exposure"
    elif not deltas.baseline:
        return f"First scan of {target}"
    elif deltas.new_vulnerabilities:
        head = _count(deltas.new_vulnerabilities, "new finding", "new findings")
    elif deltas.new_hosts or deltas.new_services:
        head = "New assets"
    else:
        head = "Partial coverage"
    return f"{head} on {target}"


def _digest_body(counts: dict, deltas: ScanDeltas) -> str:
    if not deltas.baseline:
        body = f"No earlier run to compare against. This run found {scan_count_summary(counts)}."
    else:
        detail = _severity_phrase(deltas.vulnerability_counts)
        parts = [
            text
            for text, n in (
                (_count(deltas.new_hosts, "new host", "new hosts"), deltas.new_hosts),
                (
                    _count(deltas.new_services, "new service", "new services"),
                    deltas.new_services,
                ),
                (
                    _count(deltas.new_vulnerabilities, "new finding", "new findings")
                    + (f" ({detail})" if detail else ""),
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
    if deltas.dropped_hosts:
        body += (
            f" Testing stopped on {_count(deltas.dropped_hosts, 'host', 'hosts')} "
            f"after repeated errors, so coverage there is partial."
        )
    return body


def scan_digest(
    scan_id: str, target: str, counts: dict, deltas: ScanDeltas
) -> dict | None:
    """One row per run; None when there is nothing to say."""
    if not deltas.worth_reporting(counts):
        return None

    if deltas.critical or deltas.kev:
        severity = NotificationSeverity.ERROR
    elif deltas.severe or deltas.sensitive_services or deltas.dropped_hosts:
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


def scan_failed(scan_id: str, target: str, engine: str, error: str) -> dict:
    return {
        "type": NotificationType.SCAN,
        "severity": NotificationSeverity.WARNING,
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
    """Only hosts this target has never flagged before, so a repeat scan says nothing."""
    if not leads:
        return None
    critical = [x for x in leads if x.band == InterestBand.CRITICAL.value]
    severity = NotificationSeverity.WARNING if critical else NotificationSeverity.INFO
    head = _count(len(leads), "new asset", "new assets")
    title = f"{head} flagged as an exposure on {target}"
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
    return f"• {shift.cve} · {shift.target} — {shift.finding}"


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
    body += "\nNothing was rescanned. The exploitation feeds changed."
    return {
        "type": NotificationType.SCAN,
        "severity": severity,
        "title": title,
        "message": body,
        "metadata": {"kind": "threat_intel"},
    }


@dataclass
class BountyChange:
    kind: str
    program: str
    handle: str
    asset: str | None = None


def _bounty_line(change: "BountyChange") -> str:
    what = f" — {change.asset}" if change.asset else ""
    return f"• {event_spec(change.kind).label} · {change.program}{what}"


def bounty_changes(changes: list["BountyChange"], shown: int = 6) -> dict | None:
    """Delta-only: what a program changed since the last sync."""
    if not changes:
        return None
    stop = [c for c in changes if c.kind == BountyEvent.WENT_OUT_OF_SCOPE.value]
    fresh = [
        c
        for c in changes
        if c.kind in {BountyEvent.PROGRAM_ADDED.value, BountyEvent.SCOPE_ADDED.value}
    ]
    severity = NotificationSeverity.WARNING if stop else NotificationSeverity.INFO
    if stop:
        title = _count(len(stop), "asset", "assets") + " went out of scope"
    elif fresh:
        title = _count(len(fresh), "change", "changes") + " worth looking at"
    else:
        title = _count(len(changes), "program change", "program changes")
    body = "\n".join(_bounty_line(c) for c in changes[:shown])
    if len(changes) > shown:
        body += f"\n… and {len(changes) - shown} more"
    return {
        "type": NotificationType.INTEGRATION,
        "severity": severity,
        "title": title,
        "message": body,
        "metadata": {"kind": "bounty_programs"},
    }
