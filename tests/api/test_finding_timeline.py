from __future__ import annotations

from datetime import timedelta

import pytest
import sqlalchemy as sa
from fastapi import HTTPException

from app.services.finding_timeline import FindingTimelineService
from shared.definitions.timeline import (
    CheckFlag,
    CheckState,
    FindingGroup,
    FindingState,
    FindingTimelineMode,
    Observation,
)
from shared.definitions.vulnerabilities import VulnState
from shared.models.timeline import FindingTimelineFilter
from shared.models.vulnerability import Vulnerability

pytestmark = pytest.mark.api

RAN = {
    "subdomain_discovery": "success",
    "http_probe": "success",
    "vulnerability_scan": "success",
}
NO_VULN = {"subdomain_discovery": "success", "http_probe": "success"}
PARTIAL = {**RAN, "vulnerability_scan": "partial"}

HOST = "www.example.com"
OTHER = "api.example.com"
GIT = "exposed-git"
XMLRPC = "wordpress-xmlrpc"


async def _runs(estate, now, count: int, stages=RAN, *, scope: str = "full"):
    stamps = [now - timedelta(days=count - 1 - i) for i in range(count)]
    for i, at in enumerate(stamps):
        await estate.scan("example.com", f"run{i}", at=at, scope=scope)
        await estate.activity(f"run{i}", stages)
    return stamps


async def _library(estate, now, *templates: str):
    await estate.templates(
        [(t, "high") for t in templates], at=now - timedelta(days=400)
    )


async def _search(estate, scan: str, **kw):
    return await FindingTimelineService(estate.session).search(
        estate.project_id, estate.scans[scan], FindingTimelineFilter(**kw)
    )


def _item(result, fingerprint: str):
    return next(i for i in result.items if i.finding.fingerprint == fingerprint)


def _states(item) -> list[str]:
    return [c.state for c in item.cells]


async def test_a_run_without_a_vulnerability_stage_is_not_observed(estate, now):
    stamps = await _runs(estate, now, 2, NO_VULN)
    await _library(estate, now, GIT)
    await estate.vulns("run0", [(GIT, "high")], at=stamps[0])

    result = await _search(estate, "run1")

    assert [s.observation for s in result.scans] == [Observation.UNOBSERVED.value] * 2
    item = _item(result, GIT)
    assert _states(item) == [FindingState.OPEN.value, FindingState.UNOBSERVED.value]
    assert item.group == FindingGroup.OPEN.value
    assert item.not_tested_runs == 1


async def test_a_finding_is_fixed_only_when_the_run_tested_for_it(estate, now):
    stamps = await _runs(estate, now, 3)
    await _library(estate, now, GIT)
    await estate.vulns("run0", [(GIT, "high")], at=stamps[0])
    await estate.vulns("run1", [(GIT, "high")], at=stamps[1])
    await estate.surface("run2", [HOST])

    result = await _search(estate, "run2")

    item = _item(result, GIT)
    assert _states(item) == [
        FindingState.OPEN.value,
        FindingState.OPEN.value,
        FindingState.FIXED.value,
    ]
    assert item.group == FindingGroup.FIXED.value
    assert item.state == FindingState.FIXED.value
    assert item.fixed_scan_id == estate.scans["run2"]
    assert item.fixed_at == stamps[2]
    assert item.open_since == stamps[0]
    assert item.open_days == 2
    assert item.tested_runs == 3
    assert item.last_change_scan_id == estate.scans["run2"]
    assert [s.state for s in item.segments] == [
        FindingState.OPEN.value,
        FindingState.FIXED.value,
    ]
    assert [(s.start, s.end, s.days) for s in item.segments] == [(0, 1, 2), (2, 2, 0)]
    assert result.counts[FindingGroup.FIXED.value] == 1
    assert result.stats.fixed == 1
    assert result.stats.fixed_median_days == 2
    assert result.stats.open_now == 0
    assert result.stats.open_delta == -1


async def test_an_absent_finding_on_an_unscanned_host_is_not_tested(estate, now):
    stamps = await _runs(estate, now, 2)
    await _library(estate, now, GIT)
    await estate.vulns("run0", [(GIT, "high")], at=stamps[0])
    await estate.surface("run1", [OTHER])

    item = _item(await _search(estate, "run1"), GIT)

    assert _states(item) == [FindingState.OPEN.value, FindingState.NOT_TESTED.value]
    assert item.group == FindingGroup.OPEN.value
    assert item.state == FindingState.NOT_TESTED.value
    assert item.not_tested_runs == 1
    assert item.open_days == 1


async def test_a_check_the_run_did_not_select_is_not_tested(estate, now):
    stamps = await _runs(estate, now, 2)
    await estate.vulns("run0", [(GIT, "high")], at=stamps[0])
    await estate.surface("run1", [HOST])

    item = _item(await _search(estate, "run1"), GIT)

    assert item.state == FindingState.NOT_TESTED.value


async def test_a_partial_vulnerability_scan_confirms_nothing(estate, now):
    stamps = await _runs(estate, now, 2, PARTIAL)
    await _library(estate, now, GIT)
    await estate.vulns("run0", [(GIT, "high")], at=stamps[0])
    await estate.surface("run1", [HOST])

    result = await _search(estate, "run1")

    assert result.scans[1].observation == Observation.PARTIAL.value
    assert _item(result, GIT).state == FindingState.NOT_TESTED.value


async def test_a_finding_back_after_a_fix_is_regressed(estate, now):
    stamps = await _runs(estate, now, 4)
    await _library(estate, now, GIT)
    await estate.vulns("run0", [(GIT, "high")], at=stamps[0])
    await estate.surface("run1", [HOST])
    await estate.surface("run2", [HOST])
    await estate.vulns("run3", [(GIT, "high")], at=stamps[3])

    result = await _search(estate, "run3")

    item = _item(result, GIT)
    assert _states(item) == [
        FindingState.OPEN.value,
        FindingState.FIXED.value,
        FindingState.FIXED.value,
        FindingState.REGRESSED.value,
    ]
    assert item.group == FindingGroup.REGRESSED.value
    assert item.regressions == 1
    assert item.returned_scan_id == estate.scans["run3"]
    assert item.returned_at == stamps[3]
    assert item.open_since == stamps[3]
    assert item.open_days == 0
    assert item.fixed_scan_id is None
    assert item.last_change_scan_id == estate.scans["run3"]
    assert result.stats.regressed == 1
    assert result.stats.open_now == 1
    assert result.stats.runs[1].fixed == 1
    assert result.stats.runs[3].regressed == 1
    assert result.stats.runs[3].open == {"high": 1}


async def test_a_first_sighting_in_the_viewed_scan_is_new(estate, now):
    stamps = await _runs(estate, now, 3)
    await _library(estate, now, GIT, XMLRPC)
    for i in range(3):
        await estate.vulns(f"run{i}", [(GIT, "high")], at=stamps[i])
        await estate.surface(f"run{i}", [HOST])
    await estate.vulns("run2", [(XMLRPC, "medium")], at=stamps[2])

    result = await _search(estate, "run2")

    item = _item(result, XMLRPC)
    assert item.is_new is True
    assert item.group == FindingGroup.NEW.value
    assert _states(item) == [
        FindingState.UNSEEN.value,
        FindingState.UNSEEN.value,
        FindingState.OPEN.value,
    ]
    assert item.tested_runs == 3
    assert item.segments[0].start == 2
    assert result.counts[FindingGroup.NEW.value] == 1
    assert result.counts[FindingGroup.OPEN.value] == 1
    assert result.stats.open_now == 2
    assert result.stats.open_delta == 1
    assert result.stats.oldest_open_name == "Exposed Git"
    assert result.stats.oldest_open_days == 2
    assert [i.group for i in result.items] == [
        FindingGroup.NEW.value,
        FindingGroup.OPEN.value,
    ]


async def test_a_set_aside_finding_is_never_counted_open(estate, now):
    stamps = await _runs(estate, now, 2)
    await _library(estate, now, GIT)
    await estate.vulns("run0", [(GIT, "high")], at=stamps[0])
    await estate.vulns("run1", [(GIT, "high")], at=stamps[1])
    await estate.triage("example.com", GIT, VulnState.FALSE_POSITIVE.value)

    result = await _search(estate, "run1")

    item = _item(result, GIT)
    assert item.group == FindingGroup.SET_ASIDE.value
    assert item.triage_state == VulnState.FALSE_POSITIVE.value
    assert result.counts[FindingGroup.SET_ASIDE.value] == 1
    assert result.stats.open_now == 0
    assert result.stats.runs[1].open == {}
    assert result.stats.oldest_open_days is None


async def test_the_query_narrows_the_findings_and_the_counts(estate, now):
    stamps = await _runs(estate, now, 2)
    await _library(estate, now, GIT, XMLRPC)
    await estate.vulns("run0", [(GIT, "high"), (XMLRPC, "medium")], at=stamps[0])
    await estate.vulns("run1", [(GIT, "high"), (XMLRPC, "medium")], at=stamps[1])

    result = await _search(estate, "run1", q="severity:high")

    assert [i.finding.fingerprint for i in result.items] == [GIT]
    assert result.counts["all"] == 1
    assert result.stats.open_now == 1
    assert result.total == 1


async def test_a_group_flag_pages_that_group_alone(estate, now):
    stamps = await _runs(estate, now, 2)
    await _library(estate, now, GIT, XMLRPC)
    await estate.vulns("run0", [(GIT, "high"), (XMLRPC, "medium")], at=stamps[0])
    await estate.vulns("run1", [(XMLRPC, "medium")], at=stamps[1])
    await estate.surface("run1", [HOST])

    result = await _search(estate, "run1", flag=FindingGroup.FIXED.value, limit=10)

    assert [i.finding.fingerprint for i in result.items] == [GIT]
    assert result.total == 1
    assert result.counts[FindingGroup.OPEN.value] == 1
    assert result.counts["all"] == 2
    second = await _search(estate, "run1", limit=1, offset=1)
    assert [i.finding.fingerprint for i in second.items] == [GIT]
    assert second.total == 2


async def test_a_syntax_error_comes_back_in_the_result(estate, now):
    await _runs(estate, now, 2)

    result = await _search(estate, "run1", q="severity:")

    assert result.error is not None
    assert result.items == []


async def test_a_focused_run_has_no_timeline(estate, now):
    await _runs(estate, now, 1, scope="focused")

    with pytest.raises(HTTPException) as exc:
        await _search(estate, "run0")
    assert exc.value.status_code == 422


async def test_by_check_counts_hosts_per_run(estate, now):
    stamps = await _runs(estate, now, 3)
    await _library(estate, now, GIT)
    for host in (HOST, OTHER):
        await estate.vulns(
            "run0", [(f"{GIT}-{host}", "high")], at=stamps[0], host=host, template=GIT
        )
        await estate.vulns(
            "run1", [(f"{GIT}-{host}", "high")], at=stamps[1], host=host, template=GIT
        )
    await estate.vulns("run2", [(f"{GIT}-{HOST}", "high")], at=stamps[2], template=GIT)
    await estate.surface("run2", [HOST, OTHER])

    result = await _search(estate, "run2", mode=FindingTimelineMode.CHECKS.value)

    assert result.mode == FindingTimelineMode.CHECKS
    row = result.checks[0]
    assert row.template_id == GIT
    assert [c.hosts for c in row.cells] == [2, 2, 1]
    assert [c.state for c in row.cells] == [CheckState.TESTED.value] * 3
    assert row.cells[2].delta == -1
    assert row.cells[2].removed == [OTHER]
    assert row.flags == [CheckFlag.SHRANK.value]
    assert row.hosts_now == 1
    assert row.peak == 2
    assert row.last_change_scan_id == estate.scans["run2"]
    assert result.check_stats.checks == 1
    assert result.check_stats.shrank == 1
    assert result.counts[CheckFlag.SHRANK.value] == 1


async def test_by_check_marks_runs_before_the_library_held_the_check(estate, now):
    stamps = await _runs(estate, now, 3)
    await estate.templates([(GIT, "high")], at=stamps[1])
    await estate.vulns("run1", [(GIT, "high")], at=stamps[1])
    await estate.vulns("run2", [(GIT, "high")], at=stamps[2])

    result = await _search(estate, "run2", mode=FindingTimelineMode.CHECKS.value)

    row = result.checks[0]
    assert [c.state for c in row.cells] == [
        CheckState.NOT_IN_LIBRARY.value,
        CheckState.TESTED.value,
        CheckState.TESTED.value,
    ]
    assert row.library_scan_id == estate.scans["run1"]
    assert row.flags == [CheckFlag.LIBRARY_NEW.value]
    assert result.check_stats.library_new == 1


async def test_by_check_reports_a_cleared_check(estate, now):
    stamps = await _runs(estate, now, 2)
    await _library(estate, now, GIT)
    await estate.vulns("run0", [(GIT, "high")], at=stamps[0])
    await estate.surface("run1", [HOST])

    result = await _search(estate, "run1", mode="checks")

    row = result.checks[0]
    assert [c.hosts for c in row.cells] == [1, 0]
    assert row.cells[1].state == CheckState.TESTED.value
    assert row.flags == [CheckFlag.CLEARED.value]
    assert result.check_stats.cleared == 1


async def test_by_check_flag_filters_the_rows(estate, now):
    stamps = await _runs(estate, now, 2)
    await _library(estate, now, GIT, XMLRPC)
    await estate.vulns("run0", [(GIT, "high")], at=stamps[0])
    await estate.vulns("run1", [(GIT, "high")], at=stamps[1])
    await estate.vulns(
        "run0", [(f"{XMLRPC}-{HOST}", "medium")], at=stamps[0], template=XMLRPC
    )
    for host in (HOST, OTHER):
        await estate.vulns(
            "run1",
            [(f"{XMLRPC}-{host}", "medium")],
            at=stamps[1],
            host=host,
            template=XMLRPC,
        )
    await estate.surface("run1", [HOST, OTHER])

    result = await _search(estate, "run1", mode="checks", flag=CheckFlag.SPREAD.value)

    assert [r.template_id for r in result.checks] == [XMLRPC]
    assert result.total == 1
    assert result.counts["all"] == 2


async def test_severity_sort_puts_critical_first_on_asc(estate, now):
    stamps = await _runs(estate, now, 1)
    await _library(estate, now, GIT, XMLRPC)
    await estate.vulns("run0", [(GIT, "high"), (XMLRPC, "medium")], at=stamps[0])
    await estate.vulns("run0", [("rce", "critical")], at=stamps[0], host=OTHER)

    result = await _search(estate, "run0", sort="severity", order="asc")

    assert [i.finding.severity for i in result.items] == ["critical", "high", "medium"]
    checks = await _search(estate, "run0", mode="checks", sort="severity", order="asc")
    assert [r.severity for r in checks.checks] == ["critical", "high", "medium"]


async def test_a_flag_from_the_other_mode_is_ignored(estate, now):
    stamps = await _runs(estate, now, 2)
    await _library(estate, now, GIT)
    await estate.vulns("run0", [(GIT, "high")], at=stamps[0])
    await estate.vulns("run1", [(GIT, "high")], at=stamps[1])

    checks = await _search(estate, "run1", mode="checks", flag=FindingGroup.FIXED.value)
    lives = await _search(estate, "run1", flag=CheckFlag.SPREAD.value)

    assert checks.total == 1
    assert lives.total == 1


async def test_a_viewed_run_without_a_scan_claims_no_open_count(estate, now):
    stamps = await _runs(estate, now, 2, NO_VULN)
    await _library(estate, now, GIT)
    await estate.vulns("run0", [(GIT, "high")], at=stamps[0])

    result = await _search(estate, "run1")
    checks = await _search(estate, "run1", mode="checks")

    assert result.stats.open_now is None
    assert result.stats.open_delta is None
    assert result.stats.untested == 1
    assert result.counts[FindingGroup.OPEN.value] == 1
    assert checks.checks[0].hosts_now is None
    assert checks.checks[0].flags == []


async def test_a_regression_fixed_again_is_fixed(estate, now):
    stamps = await _runs(estate, now, 4)
    await _library(estate, now, GIT)
    await estate.vulns("run0", [(GIT, "high")], at=stamps[0])
    await estate.surface("run1", [HOST])
    await estate.vulns("run2", [(GIT, "high")], at=stamps[2])
    await estate.surface("run3", [HOST])

    result = await _search(estate, "run3")

    item = _item(result, GIT)
    assert item.group == FindingGroup.FIXED.value
    assert item.state == FindingState.FIXED.value
    assert item.regressions == 1
    assert item.open_since == stamps[2]
    assert item.open_days == 1
    assert result.stats.fixed == 1
    assert result.stats.regressed == 0
    assert result.stats.oldest_open_days is None
    assert sum(p.fixed for p in result.stats.runs) == 2


async def test_by_check_does_not_remove_a_host_the_run_did_not_scan(estate, now):
    stamps = await _runs(estate, now, 3)
    await _library(estate, now, GIT)
    for host in (HOST, OTHER):
        await estate.vulns(
            "run0", [(f"{GIT}-{host}", "high")], at=stamps[0], host=host, template=GIT
        )
    await estate.vulns("run1", [(f"{GIT}-{HOST}", "high")], at=stamps[1], template=GIT)
    await estate.surface("run1", [HOST])
    await estate.surface("run2", [OTHER])

    row = (await _search(estate, "run2", mode="checks")).checks[0]

    assert [c.state for c in row.cells] == [CheckState.TESTED.value] * 3
    assert [c.hosts for c in row.cells] == [2, 1, 0]
    assert row.cells[1].removed == []
    assert row.cells[1].delta == 0
    assert row.cells[2].removed == [OTHER]
    assert row.cells[2].delta == -1
    assert row.hosts_now == 0
    assert row.flags == []


async def test_a_replay_follows_a_suppressed_source(estate, now):
    stamps = await _runs(estate, now, 1)
    await _library(estate, now, GIT)
    await estate.vulns("run0", [(GIT, "high")], at=stamps[0])
    source = await estate.session.scalar(
        sa.select(Vulnerability.id).where(Vulnerability.fingerprint == GIT)
    )
    await estate.vulns("run0", [(f"{GIT}-replay", "high")], at=stamps[0], host=OTHER)
    await estate.session.execute(
        sa.update(Vulnerability)
        .where(Vulnerability.fingerprint == f"{GIT}-replay")
        .values(replayed_from_id=source, template_id=GIT)
    )
    await estate.triage("example.com", GIT, VulnState.ACCEPTED.value)

    result = await _search(estate, "run0")

    assert {i.group for i in result.items} == {FindingGroup.SET_ASIDE.value}
    assert result.counts[FindingGroup.SET_ASIDE.value] == 2
