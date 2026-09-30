from __future__ import annotations

from datetime import UTC, datetime

import pytest

from shared.definitions.new_checks import (
    FOLLOW_UP_STAGES,
    MAX_TEMPLATE_IDS,
    NEW_CHECKS_KEY,
    RUN_LABEL,
    run_label,
)
from shared.definitions.notifications import NewChecksResult, new_checks_result
from shared.enums.notification import NotificationSeverity, NotificationType
from shared.models.notification_channel import DEFAULT_PREFERENCE_TYPES
from shared.models.vuln_template import TemplateSelection
from shared.services.new_checks import window_end
from shared.services.vuln_templates import selection_predicate
from stages.vulnerability_scan.config import VulnerabilityScanConfig

pytestmark = pytest.mark.pipeline


def test_the_run_is_named_after_its_check_count():
    assert run_label(3) == f"{RUN_LABEL} · 3"
    assert FOLLOW_UP_STAGES[-1] == "vulnerability_scan"
    assert NEW_CHECKS_KEY.startswith("_")


def test_only_these_checks_reaches_the_selection():
    cfg = VulnerabilityScanConfig(template_ids=["CVE-2025-1", "CVE-2025-2"])
    selection = cfg.selection()
    assert selection.template_ids == ["CVE-2025-1", "CVE-2025-2"]
    sql = str(selection_predicate(selection).compile())
    assert "vuln_templates.template_id IN" in sql


def test_an_empty_id_list_does_not_narrow():
    sql = str(selection_predicate(TemplateSelection(severities=["high"])).compile())
    assert "template_id IN" not in sql


def test_the_window_end_moves_back_to_the_last_row_when_capped():
    until = datetime(2026, 9, 20, tzinfo=UTC)
    few = [("a", datetime(2026, 9, 19, tzinfo=UTC))]
    assert window_end(few, until) == until
    capped = [
        (str(i), datetime(2026, 9, 19, i % 24, tzinfo=UTC))
        for i in range(MAX_TEMPLATE_IDS)
    ]
    assert window_end(capped, until) == capped[-1][1]


def test_the_run_notice_is_sent_only_with_findings():
    quiet = NewChecksResult(scan_id="s", target="example.com", checks=3, findings=0)
    assert new_checks_result(quiet) is None

    loud = NewChecksResult(
        scan_id="s",
        target="example.com",
        checks=3,
        findings=2,
        by_severity={"critical": 1, "low": 1},
    )
    payload = new_checks_result(loud)
    assert payload is not None
    assert payload["severity"] is NotificationSeverity.ERROR
    assert payload["title"] == "New checks found 2 findings on example.com"
    assert payload["message"] == "2 findings · 1 critical, 1 low\n3 new checks tested"
    assert payload["metadata"]["url"] == "/scans/s?tab=vulnerabilities"


def test_new_checks_is_a_default_channel_category():
    assert NotificationType.NEW_CHECKS.value in DEFAULT_PREFERENCE_TYPES
