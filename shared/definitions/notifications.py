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
