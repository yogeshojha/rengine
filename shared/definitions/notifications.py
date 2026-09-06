"""Notification templates: one interrupt per event, never a copy of the activity log."""

from dataclasses import dataclass, field

from shared.definitions.vulnerabilities import (
    ALERT_SEVERITIES,
    SEVERITY_LABELS,
    SEVERITY_ORDER,
    Severity,
)
from shared.enums.notification import NotificationSeverity, NotificationType


def _count(n: int, singular: str, plural: str) -> str:
    return f"{n:,} {singular if n == 1 else plural}"


def whois_enrichment_incomplete(success: int, failed: int, total: int) -> dict | None:
    if not failed:
        return None
    return {
        "type": NotificationType.TARGET,
        "severity": NotificationSeverity.WARNING,
        "title": "WHOIS lookup failed",
        "message": (
            f"WHOIS could not be resolved for {failed} of {total} "
            f"{'target' if total == 1 else 'targets'}"
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
    success: int, failed: int, skipped: int, total: int
) -> dict | None:
    if not failed:
        return None
    return {
        "type": NotificationType.TARGET,
        "severity": NotificationSeverity.WARNING,
        "title": "BGP enrichment failed",
        "message": (
            f"BGP data could not be resolved for {failed} of {total} "
            f"{'target' if total == 1 else 'targets'}"
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
