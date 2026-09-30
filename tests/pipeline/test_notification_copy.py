from __future__ import annotations

import pytest

from shared.definitions.bounty_programs import BountyEvent
from shared.definitions.notifications import (
    BountyChange,
    ScanDeltas,
    bounty_changes,
    scan_digest,
    schedule_not_started,
)
from shared.enums.notification import NotificationSeverity, NotificationType

pytestmark = pytest.mark.pipeline

COUNTS = {
    "subdomains_found": 514,
    "ips_found": 101,
    "open_ports_found": 80,
    "http_assets_found": 105,
    "vulnerabilities_found": 51,
    "endpoints_found": 2380,
    "secrets_found": 12,
}
INVENTORY = "514 web assets · 101 addresses · 80 services · 2,380 endpoints"


def test_a_first_scan_leads_with_its_worst_fact_and_ends_with_the_inventory():
    payload = scan_digest(
        "s",
        "ntc.net.np",
        COUNTS,
        ScanDeltas(
            vulnerability_counts={"high": 3, "medium": 20, "low": 28},
            new_secrets=2,
            sensitive_services=4,
            exposures=16,
        ),
    )
    assert payload is not None
    assert payload["title"] == "2 exposed secrets on ntc.net.np"
    assert payload["severity"] is NotificationSeverity.WARNING
    assert payload["type"] is NotificationType.SCAN
    assert payload["message"].split("\n") == [
        "51 findings · 3 high, 20 medium, 28 low",
        "4 administrative or datastore ports open",
        "16 assets flagged as exposures",
        INVENTORY,
    ]
    assert payload["metadata"]["url"] == "/scans/s?tab=secrets"


def test_a_first_scan_with_a_critical_finding_is_an_error():
    payload = scan_digest(
        "s", "gov.np", COUNTS, ScanDeltas(vulnerability_counts={"critical": 2}, kev=1)
    )
    assert payload is not None
    assert payload["title"] == "2 critical findings on gov.np"
    assert payload["severity"] is NotificationSeverity.ERROR
    assert payload["type"] is NotificationType.VULNERABILITY
    assert payload["message"].split("\n") == [
        "2 findings · 2 critical",
        "1 known exploited",
        INVENTORY,
    ]


def test_a_first_scan_with_nothing_risky_says_it_completed():
    payload = scan_digest("s", "example.com", COUNTS, ScanDeltas())
    assert payload is not None
    assert payload["title"] == "Scan completed on example.com"
    assert payload["severity"] is NotificationSeverity.INFO
    assert payload["message"] == INVENTORY
    assert payload["metadata"]["url"] == "/scans/s"


def test_a_repeat_scan_carries_every_change_risk_first():
    deltas = ScanDeltas(
        baseline=True,
        new_hosts=11,
        new_services=4,
        new_vulnerabilities=5,
        vulnerability_counts={"high": 2, "medium": 3},
        new_secrets=1,
        exposures=356,
        dropped_hosts=3,
    )
    payload = scan_digest("s", "go.id", COUNTS, deltas)
    assert payload is not None
    assert payload["title"] == "1 exposed secret on go.id"
    assert payload["severity"] is NotificationSeverity.WARNING
    assert payload["message"].split("\n") == [
        "5 new findings · 2 high, 3 medium",
        "11 new web assets · 4 new services",
        "356 new assets flagged as exposures",
        "3 web assets not fully tested",
    ]


def test_a_repeat_scan_with_nothing_new_sends_nothing():
    assert scan_digest("s", "example.com", COUNTS, ScanDeltas(baseline=True)) is None


def test_the_body_never_repeats_the_title():
    hosts = scan_digest(
        "s",
        "tigo.com.co",
        COUNTS,
        ScanDeltas(baseline=True, new_hosts=33952, exposures=8, dropped_hosts=51),
    )
    assert hosts is not None
    assert hosts["title"] == "33,952 new web assets on tigo.com.co"
    assert hosts["severity"] is NotificationSeverity.INFO
    assert hosts["message"].split("\n") == [
        "8 new assets flagged as exposures",
        "51 web assets not fully tested",
    ]

    findings = scan_digest(
        "s",
        "gov.cy",
        COUNTS,
        ScanDeltas(
            baseline=True,
            new_vulnerabilities=4,
            vulnerability_counts={"medium": 1, "low": 3},
        ),
    )
    assert findings is not None
    assert findings["title"] == "4 new findings on gov.cy"
    assert findings["message"] == "1 medium, 3 low"

    services = scan_digest(
        "s", "go.id", COUNTS, ScanDeltas(baseline=True, new_services=7)
    )
    assert services is not None
    assert services["title"] == "7 new services on go.id"
    assert services["message"] == ""
    assert services["metadata"]["url"] == "/scans/s?tab=services"

    posture = scan_digest(
        "s", "claro.com.co", COUNTS, ScanDeltas(baseline=True, posture_regressions=1)
    )
    assert posture is not None
    assert posture["title"] == "SPF or DMARC weakened on claro.com.co"
    assert posture["message"] == ""


def _change(kind: str, program: str = "Acme", asset: str | None = "a.acme.com"):
    return BountyChange(kind=kind, program=program, handle="acme", asset=asset)


def test_the_bounty_title_counts_what_the_body_lists():
    added = BountyEvent.SCOPE_ADDED.value
    opened = BountyEvent.SUBMISSIONS_OPENED.value
    stop = BountyEvent.WENT_OUT_OF_SCOPE.value

    only_added = bounty_changes([_change(added), _change(added)])
    assert only_added is not None
    assert only_added["title"] == "2 scope additions"

    mixed = bounty_changes([_change(added), _change(opened, asset=None)])
    assert mixed is not None
    assert mixed["title"] == "2 program updates"

    stopped = bounty_changes([_change(opened, asset=None), _change(stop)])
    assert stopped is not None
    assert stopped["title"] == "1 asset out of scope, 1 other update"
    assert stopped["severity"] is NotificationSeverity.WARNING
    assert stopped["message"].split("\n")[0] == "Now out of scope · Acme · a.acme.com"


def test_the_bounty_body_counts_the_rows_it_left_out():
    payload = bounty_changes(
        [_change(BountyEvent.SCOPE_ADDED.value)] * 6,
        counts={BountyEvent.SCOPE_ADDED.value: 80},
    )
    assert payload is not None
    assert payload["title"] == "80 scope additions"
    assert payload["message"].split("\n")[-1] == "and 74 more"


def test_a_schedule_that_did_not_start_is_an_error():
    payload = schedule_not_started("Nightly", 2, 14)
    assert payload["title"] == "Scheduled scan not started · Nightly"
    assert payload["message"] == (
        "2 of 14 targets not started. Check the schedule and the worker log."
    )
    assert payload["severity"] is NotificationSeverity.ERROR
