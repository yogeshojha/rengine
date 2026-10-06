from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from reports.data.source import ReportSource
from reports.sections.methodology.section import MethodologyConfig, MethodologySection
from shared.definitions.reports import ReportScope
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.models.target import Target

pytestmark = pytest.mark.api

NOW = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)
CONFIGURED = {
    name: {"enabled": True}
    for name in ("reverse_dns", "url_discovery", "lookalike_domains", "takeover")
}


class _Ctx:
    def __init__(self, data):
        self.data = data


async def _run(estate, stages: list[tuple[str, str, int]]) -> ReportSource:
    sid = await estate.scan("example.com", "run", at=NOW, config={"stages": CONFIGURED})
    for name, status, minute in stages:
        estate.session.add(
            ScanActivity(
                scan_id=sid,
                project_id=estate.project_id,
                name=name,
                title=name,
                status=status,
                started_at=NOW + timedelta(minutes=minute),
                completed_at=NOW + timedelta(minutes=minute + 1),
            )
        )
    await estate.session.flush()

    def build(sync):
        scan = sync.get(Scan, sid)
        target = sync.get(Target, scan.target_id)
        return ReportSource(
            sync, scope=ReportScope.SCAN.value, scan=scan, target=target
        )

    return await estate.session.run_sync(build)


async def test_the_report_lists_the_stages_the_run_started(estate):
    source = await _run(
        estate,
        [
            ("url_discovery", "partial", 2),
            ("reverse_dns", "success", 1),
            ("lookalike_domains", "skipped", 0),
            ("takeover", "aborted", 3),
        ],
    )

    built = await estate.session.run_sync(
        lambda _: MethodologySection().build(_Ctx(source), MethodologyConfig())
    )

    assert [(s["title"], s["result"]) for s in built["stages"]] == [
        ("Reverse DNS", "Success"),
        ("URL Discovery", "Partial"),
        ("Subdomain Takeover", "Aborted"),
    ]


async def test_tools_come_from_stages_that_ran(estate):
    source = await _run(
        estate,
        [("lookalike_domains", "skipped", 0), ("url_discovery", "success", 1)],
    )

    tools = await estate.session.run_sync(lambda _: source.tools_used)

    assert "katana" in tools
    assert "dnsx" not in tools


async def test_a_stage_resumed_after_a_pause_is_listed_once(estate):
    source = await _run(
        estate,
        [("reverse_dns", "aborted", 0), ("reverse_dns", "success", 5)],
    )

    results = await estate.session.run_sync(lambda _: source.stage_results)

    assert results == {"reverse_dns": "success"}
