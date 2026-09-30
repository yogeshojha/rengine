"""Sample notifications rendered through the real templates."""

from datetime import timedelta

from shared.definitions.notifications import (
    BountyChange,
    IntelShift,
    NewChecksResult,
    ScanDeltas,
    SoftwareExposure,
    WatchAlert,
    bounty_changes,
    intel_changed,
    new_checks_result,
    scan_digest,
    scan_failed,
    schedule_not_started,
    software_exposed,
    watch_alert,
)
from shared.enums.notification import NotificationSeverity, NotificationType
from shared.utils.datetime import utc_now

_SCAN_ID = "00000000-0000-0000-0000-000000000000"

_COUNTS = {
    "subdomains_found": 118,
    "ips_found": 64,
    "open_ports_found": 203,
    "http_assets_found": 87,
    "vulnerabilities_found": 9,
    "endpoints_found": 1_204,
}

DEBUG_NOTIFICATION_TEMPLATES = [
    scan_digest(
        _SCAN_ID,
        "example.com",
        _COUNTS,
        ScanDeltas(
            baseline=True,
            new_hosts=4,
            new_services=2,
            sensitive_services=1,
            new_vulnerabilities=3,
            vulnerability_counts={"critical": 1, "high": 2},
            kev=1,
            new_secrets=2,
            exposures=5,
        ),
    ),
    scan_digest(_SCAN_ID, "example.com", _COUNTS, ScanDeltas(baseline=False)),
    scan_failed(_SCAN_ID, "example.com", "Full scan", "subdomain_discovery failed"),
    schedule_not_started("Nightly estate", 2, 14),
    intel_changed(
        [
            IntelShift(
                cve="CVE-2024-3400",
                target="example.com",
                finding="GlobalProtect OS command injection",
                kind="kev",
                scan_id=_SCAN_ID,
            )
        ]
    ),
    software_exposed(
        [
            SoftwareExposure(
                cve="CVE-2021-44228",
                host="api.example.com",
                name="Log4j",
                version="2.14.1",
                severity="critical",
                is_kev=True,
                kev_ransomware=True,
            )
        ]
    ),
    bounty_changes(
        [
            BountyChange(
                kind="scope_added",
                program="Example VDP",
                handle="example",
                asset="*.example.com",
            ),
            BountyChange(
                kind="went_out_of_scope",
                program="Example VDP",
                handle="example",
                asset="legacy.example.com",
            ),
        ]
    ),
    watch_alert(
        WatchAlert(
            program="Example VDP",
            host="new.example.com",
            matched_item="*.example.com",
            status_code=200,
            title="Sign in",
            tech=("nginx", "React"),
            ips=("203.0.113.10",),
            issuer="R11",
            not_before=utc_now() - timedelta(hours=2),
            scan_id=_SCAN_ID,
        )
    ),
    new_checks_result(
        NewChecksResult(
            scan_id=_SCAN_ID,
            target="example.com",
            checks=14,
            findings=2,
            by_severity={"high": 1, "medium": 1},
        )
    ),
    {
        "type": NotificationType.SYSTEM,
        "severity": NotificationSeverity.ERROR,
        "title": "Report failed",
        "message": "Attack surface report · example.com. Check the worker log.",
        "metadata": {"url": "/reports"},
    },
]
