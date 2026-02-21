"""Notification templates - single source of truth for all notification messages."""

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
    """Entire WHOIS task failed (not individual target failures)."""
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
