from shared.enums.notification import NotificationSeverity, NotificationType


def whois_enrichment_complete(
    success: int,
    failed: int,
    total: int,
) -> dict:
    if failed == 0:
        return {
            "type": NotificationType.TARGET,
            "severity": NotificationSeverity.SUCCESS,
            "title": "WHOIS Enrichment Complete",
            "message": (
                f"WHOIS lookup completed for {success} "
                f"{'target' if success == 1 else 'targets'}."
            ),
        }
    return {
        "type": NotificationType.TARGET,
        "severity": NotificationSeverity.WARNING,
        "title": "WHOIS Enrichment Complete",
        "message": (
            f"WHOIS lookup completed: {success} succeeded, "
            f"{failed} failed out of {total} targets."
        ),
    }


def whois_enrichment_failed(error: str) -> dict:
    return {
        "type": NotificationType.TARGET,
        "severity": NotificationSeverity.ERROR,
        "title": "WHOIS Enrichment Failed",
        "message": f"WHOIS enrichment task failed: {error}",
    }


def viewdns_enrichment_complete(
    success: int, failed: int, skipped: int, total: int
) -> dict:
    if failed == 0 and skipped == 0:
        severity = NotificationSeverity.SUCCESS
        title = "ViewDNS Enrichment Complete"
        message = f"Successfully enriched {success}/{total} targets with ViewDNS data."
    elif success > 0:
        severity = NotificationSeverity.WARNING
        title = "ViewDNS Enrichment Partially Complete"
        message = (
            f"ViewDNS enrichment finished: {success} succeeded, "
            f"{failed} failed, {skipped} skipped out of {total} targets."
        )
    else:
        severity = NotificationSeverity.ERROR
        title = "ViewDNS Enrichment Failed"
        message = (
            f"ViewDNS enrichment could not complete: "
            f"{failed} failed, {skipped} skipped out of {total} targets."
        )

    return {
        "type": NotificationType.TARGET,
        "severity": severity,
        "title": title,
        "message": message,
    }


def viewdns_enrichment_failed(error: str) -> dict:
    return {
        "type": NotificationType.TARGET,
        "severity": NotificationSeverity.ERROR,
        "title": "ViewDNS Enrichment Failed",
        "message": f"ViewDNS enrichment task failed: {error}",
    }


def ripestat_enrichment_complete(
    success: int, failed: int, skipped: int, total: int
) -> dict:
    if failed == 0 and skipped == 0:
        severity = NotificationSeverity.SUCCESS
        title = "BGP Enrichment Complete"
        message = f"Successfully enriched {success} targets with BGP data."
    elif success > 0:
        severity = NotificationSeverity.WARNING
        title = "BGP Enrichment Partially Complete"
        message = (
            f"BGP enrichment finished: {success} succeeded, "
            f"{failed} failed, {skipped} skipped out of {total} targets."
        )
    else:
        severity = NotificationSeverity.ERROR
        title = "BGP Enrichment Failed"
        message = (
            f"BGP enrichment could not complete: "
            f"{failed} failed, {skipped} skipped out of {total} targets."
        )

    return {
        "type": NotificationType.TARGET,
        "severity": severity,
        "title": title,
        "message": message,
    }


def ripestat_enrichment_failed(error: str) -> dict:
    return {
        "type": NotificationType.TARGET,
        "severity": NotificationSeverity.ERROR,
        "title": "BGP Enrichment Failed",
        "message": f"BGP enrichment task failed: {error}",
    }


_SECONDS_PER_MINUTE = 60
_MINUTES_PER_HOUR = 60


def _scan_meta(scan_id: str) -> dict:
    return {"scan_id": str(scan_id), "url": f"/scans/{scan_id}"}


def _scan_duration(seconds: float | None) -> str:
    if not seconds or seconds < 0:
        return ""
    seconds = int(seconds)
    if seconds < _SECONDS_PER_MINUTE:
        return f" in {seconds}s"
    minutes, rem = divmod(seconds, _SECONDS_PER_MINUTE)
    if minutes < _MINUTES_PER_HOUR:
        return f" in {minutes}m {rem}s" if rem else f" in {minutes}m"
    hours, minutes = divmod(minutes, _MINUTES_PER_HOUR)
    return f" in {hours}h {minutes}m"


def scan_started(scan_id: str, target: str, engine: str) -> dict:
    return {
        "type": NotificationType.SCAN,
        "severity": NotificationSeverity.INFO,
        "title": "Scan Started",
        "message": f"Scan of {target} started with engine {engine}.",
        "metadata": _scan_meta(scan_id),
    }


_SCAN_COUNT_LABELS = {
    "subdomains_found": ("subdomain", "subdomains"),
    "ips_found": ("IP", "IPs"),
    "open_ports_found": ("open port", "open ports"),
    "http_assets_found": ("HTTP service", "HTTP services"),
    "vulnerabilities_found": ("vulnerability", "vulnerabilities"),
    "endpoints_found": ("endpoint", "endpoints"),
}


def scan_count_summary(counts: dict) -> str:
    parts = [
        f"{n} {singular if n == 1 else plural}"
        for col, (singular, plural) in _SCAN_COUNT_LABELS.items()
        if (n := counts.get(col, 0))
    ]
    return ", ".join(parts) if parts else "no assets"


def scan_completed(
    scan_id: str,
    target: str,
    engine: str,
    counts: dict,
    duration_seconds: float | None,
) -> dict:
    return {
        "type": NotificationType.SCAN,
        "severity": NotificationSeverity.SUCCESS,
        "title": "Scan Completed",
        "message": (
            f"Scan of {target} ({engine}) completed"
            f"{_scan_duration(duration_seconds)} — {scan_count_summary(counts)}."
        ),
        "metadata": _scan_meta(scan_id),
    }


def scan_new_subdomains(scan_id: str, target: str, count: int) -> dict:
    return {
        "type": NotificationType.SCAN,
        "severity": NotificationSeverity.INFO,
        "title": "New Subdomains Discovered",
        "message": (
            f"{count} new {'subdomain' if count == 1 else 'subdomains'} "
            f"discovered on {target}."
        ),
        "metadata": _scan_meta(scan_id),
    }


def scan_failed(scan_id: str, target: str, engine: str, error: str) -> dict:
    return {
        "type": NotificationType.SCAN,
        "severity": NotificationSeverity.ERROR,
        "title": "Scan Failed",
        "message": f"Scan of {target} ({engine}) failed: {error[:300]}",
        "metadata": _scan_meta(scan_id),
    }


def scan_cancelled(scan_id: str, target: str, engine: str) -> dict:
    return {
        "type": NotificationType.SCAN,
        "severity": NotificationSeverity.WARNING,
        "title": "Scan Cancelled",
        "message": f"Scan of {target} ({engine}) was cancelled.",
        "metadata": _scan_meta(scan_id),
    }
