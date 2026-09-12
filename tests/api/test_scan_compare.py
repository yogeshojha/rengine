from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.services.scan_compare import ScanCompareService
from shared.definitions.compare import (
    REFUSAL_REASON,
    ChangeVerb,
    Comparability,
    Refusal,
)
from shared.definitions.surface import SurfaceDimension
from shared.models.scan import Scan

pytestmark = pytest.mark.api

WEB = SurfaceDimension.WEB_ASSETS.value
VULNS = SurfaceDimension.VULNERABILITIES.value
SERVICES = SurfaceDimension.SERVICES.value

RAN_WEB = {"subdomain_discovery": "success", "http_probe": "success"}
RAN_VULNS = {"vulnerability_scan": "success"}
RAN_PORTS = {"port_scan": "success"}


def _dim(report, key: str):
    return next(d for d in report.dimensions if d.dimension == key)


ENGINE = "Standard"


async def _pair(estate, now, *, config_a=None, config_b=None):
    old = now - timedelta(hours=2)
    a = await estate.scan(
        "example.com", "first", at=old, config=config_a, engine=ENGINE
    )
    b = await estate.scan(
        "example.com", "second", at=now, config=config_b, engine=ENGINE
    )
    return a, b, old


async def test_a_host_present_in_both_runs_is_unchanged(estate, now):
    a, b, old = await _pair(estate, now)
    await estate.hosts("first", ["a.example.com"], at=old, status=200)
    await estate.hosts("second", ["a.example.com"], at=now, status=200)
    await estate.activity("first", RAN_WEB)
    await estate.activity("second", RAN_WEB)

    report = await ScanCompareService(estate.session).comparison(
        a, b, estate.project_id
    )

    web = _dim(report, WEB)
    assert web.unchanged == 1
    assert web.appeared == 0
    assert web.changed == 0
    assert web.disappeared == 0
    assert report.changes_total == 0
    assert report.headline == "Nothing changed"


async def test_appeared_changed_and_disappeared_are_counted_apart(estate, now):
    a, b, old = await _pair(estate, now)
    await estate.hosts("first", ["stays.example.com", "goes.example.com"], at=old)
    await estate.hosts("first", ["moves.example.com"], at=old, status=403)
    await estate.hosts("second", ["stays.example.com", "new.example.com"], at=now)
    await estate.hosts("second", ["moves.example.com"], at=now, status=200)
    await estate.activity("first", RAN_WEB)
    await estate.activity("second", RAN_WEB)

    report = await ScanCompareService(estate.session).comparison(
        a, b, estate.project_id
    )

    web = _dim(report, WEB)
    assert web.appeared == 1
    assert web.disappeared == 1
    assert web.changed == 1
    assert web.unchanged == 1


async def test_the_sides_of_the_diff_add_up_to_each_run(estate, now):
    a, b, old = await _pair(estate, now)
    await estate.hosts("first", ["one.example.com", "two.example.com"], at=old)
    await estate.hosts("second", ["two.example.com", "three.example.com"], at=now)
    await estate.activity("first", RAN_WEB)
    await estate.activity("second", RAN_WEB)

    report = await ScanCompareService(estate.session).comparison(
        a, b, estate.project_id
    )

    web = _dim(report, WEB)
    assert web.disappeared + web.changed + web.unchanged == web.total_baseline
    assert web.appeared + web.changed + web.unchanged == web.total_current


async def test_a_dimension_the_later_run_never_scanned_is_not_covered(estate, now):
    a, b, old = await _pair(estate, now)
    await estate.vulns("first", [("cve-a", "high")], at=old)
    await estate.activity("first", RAN_VULNS)
    await estate.activity("second", {"http_probe": "success"})

    report = await ScanCompareService(estate.session).comparison(
        a, b, estate.project_id
    )

    vulns = _dim(report, VULNS)
    assert vulns.verdict.comparability == Comparability.NOT_COVERED.value
    assert vulns.disappeared == 0, "not scanned is not the same as removed"
    assert vulns.unconfirmed == 0
    assert "Not scanned" in vulns.verdict.note


async def test_a_partial_producing_stage_leaves_missing_rows_unconfirmed(estate, now):
    a, b, old = await _pair(estate, now)
    await estate.hosts("first", ["gone.example.com"], at=old)
    await estate.hosts("second", ["other.example.com"], at=now)
    await estate.activity("first", RAN_WEB)
    await estate.activity("second", {"subdomain_discovery": "partial"})

    report = await ScanCompareService(estate.session).comparison(
        a, b, estate.project_id
    )

    web = _dim(report, WEB)
    assert web.disappeared == 0
    assert web.unconfirmed == 1
    assert web.verdict.confirmed is False
    assert web.verdict.comparability == Comparability.QUALITY_DIFFERS.value


async def test_a_stage_setting_that_differs_is_named(estate, now):
    a, b, _ = await _pair(
        estate,
        now,
        config_a={"stages": {"vulnerability_scan": {"max_minutes": 0}}},
        config_b={"stages": {"vulnerability_scan": {"max_minutes": 2}}},
    )
    await estate.activity("first", RAN_VULNS)
    await estate.activity("second", RAN_VULNS)

    report = await ScanCompareService(estate.session).comparison(
        a, b, estate.project_id
    )

    vulns = _dim(report, VULNS)
    assert vulns.verdict.comparability == Comparability.SETTINGS_DIFFER.value
    assert [s.field for s in vulns.verdict.settings] == ["max_minutes"]
    assert (vulns.verdict.settings[0].before, vulns.verdict.settings[0].after) == (
        "0",
        "2",
    )
    assert report.comparability == Comparability.SETTINGS_DIFFER.value
    assert _dim(report, WEB).verdict.compared is False


async def test_a_reordered_list_setting_is_not_a_difference(estate, now):
    a, b, _ = await _pair(
        estate,
        now,
        config_a={"stages": {"subdomain_discovery": {"sources": ["a", "b"]}}},
        config_b={"stages": {"subdomain_discovery": {"sources": ["b", "a"]}}},
    )
    await estate.activity("first", RAN_WEB)
    await estate.activity("second", RAN_WEB)

    report = await ScanCompareService(estate.session).comparison(
        a, b, estate.project_id
    )

    assert report.setting_diff == []
    assert _dim(report, WEB).verdict.comparability == Comparability.LIKE_FOR_LIKE.value
    assert report.comparability == Comparability.LIKE_FOR_LIKE.value


async def test_a_reordered_technology_list_is_not_a_change(estate, now):
    a, b, old = await _pair(estate, now)
    await estate.hosts("first", ["a.example.com"], at=old, tech=["nginx", "php"])
    await estate.hosts("second", ["a.example.com"], at=now, tech=["php", "nginx"])
    await estate.activity("first", RAN_WEB)
    await estate.activity("second", RAN_WEB)

    report = await ScanCompareService(estate.session).comparison(
        a, b, estate.project_id
    )

    assert _dim(report, WEB).changed == 0


async def test_the_count_is_a_promise(estate, now):
    a, b, old = await _pair(estate, now)
    await estate.hosts("first", ["gone.example.com", "stays.example.com"], at=old)
    await estate.hosts("second", ["stays.example.com", "new.example.com"], at=now)
    await estate.activity("first", RAN_WEB)
    await estate.activity("second", RAN_WEB)

    service = ScanCompareService(estate.session)
    report = await service.comparison(a, b, estate.project_id)
    web = _dim(report, WEB)
    rows = await service.rows(
        baseline_id=a,
        current_id=b,
        project_id=estate.project_id,
        dimension=WEB,
        verbs=[],
        page=1,
        size=50,
    )

    listed = web.appeared + web.changed + web.disappeared + web.unconfirmed
    assert rows.total == listed
    assert len(rows.items) == listed


async def test_one_verb_returns_only_its_own_rows(estate, now):
    a, b, old = await _pair(estate, now)
    await estate.hosts("first", ["gone.example.com"], at=old)
    await estate.hosts("second", ["new.example.com"], at=now)
    await estate.activity("first", RAN_WEB)
    await estate.activity("second", RAN_WEB)

    rows = await ScanCompareService(estate.session).rows(
        baseline_id=a,
        current_id=b,
        project_id=estate.project_id,
        dimension=WEB,
        verbs=[ChangeVerb.APPEARED.value],
        page=1,
        size=50,
    )

    assert rows.total == 1
    assert rows.items[0].title == "new.example.com"
    assert rows.items[0].verb == ChangeVerb.APPEARED.value


async def test_a_dropped_authentication_outranks_a_new_host(estate, now):
    a, b, old = await _pair(estate, now)
    await estate.hosts("first", ["locked.example.com"], at=old, status=403)
    await estate.hosts("second", ["locked.example.com"], at=now, status=200)
    await estate.hosts("second", ["new.example.com"], at=now, status=200)
    await estate.activity("first", RAN_WEB)
    await estate.activity("second", RAN_WEB)

    rows = await ScanCompareService(estate.session).rows(
        baseline_id=a,
        current_id=b,
        project_id=estate.project_id,
        dimension=WEB,
        verbs=[],
        page=1,
        size=50,
    )

    assert [r.signal for r in rows.items] == ["auth_dropped", "host_appeared"]


async def test_a_sensitive_port_opening_is_named(estate, now):
    a, b, old = await _pair(estate, now)
    await estate.ports("first", [("10.0.0.1", 443, "https")], at=old)
    await estate.ports(
        "second", [("10.0.0.1", 443, "https"), ("10.0.0.1", 3306, "mysql")], at=now
    )
    await estate.activity("first", RAN_PORTS)
    await estate.activity("second", RAN_PORTS)

    rows = await ScanCompareService(estate.session).rows(
        baseline_id=a,
        current_id=b,
        project_id=estate.project_id,
        dimension=SERVICES,
        verbs=[],
        page=1,
        size=50,
    )

    assert rows.total == 1
    assert rows.items[0].signal == "sensitive_service_opened"
    assert rows.items[0].sensitive is True
    assert rows.items[0].title == "10.0.0.1:3306"


async def test_a_focused_run_is_refused_against_a_full_one(estate, now):
    old = now - timedelta(hours=2)
    a = await estate.scan("example.com", "census", at=old)
    b = await estate.scan("example.com", "rescan", at=now, scope="focused")

    with pytest.raises(HTTPException) as raised:
        await ScanCompareService(estate.session).comparison(a, b, estate.project_id)

    assert raised.value.status_code == 422
    assert "focused run" in raised.value.detail


async def test_a_run_cannot_be_compared_with_itself(estate, now):
    a = await estate.scan("example.com", "only", at=now)

    with pytest.raises(HTTPException) as raised:
        await ScanCompareService(estate.session).comparison(a, a, estate.project_id)

    assert raised.value.status_code == 422


async def test_two_targets_cannot_be_compared(estate, now):
    old = now - timedelta(hours=2)
    a = await estate.scan("one.example.com", "first", at=old)
    b = await estate.scan("two.example.com", "second", at=now)

    with pytest.raises(HTTPException) as raised:
        await ScanCompareService(estate.session).comparison(a, b, estate.project_id)

    assert raised.value.status_code == 422
    assert "same target" in raised.value.detail


async def test_the_baseline_defaults_to_the_previous_run(estate, now):
    old = now - timedelta(hours=2)
    a = await estate.scan("example.com", "first", at=old, engine=ENGINE)
    b = await estate.scan("example.com", "second", at=now, engine=ENGINE)
    await estate.activity("first", RAN_WEB)
    await estate.activity("second", RAN_WEB)

    report = await ScanCompareService(estate.session).comparison(
        None, b, estate.project_id
    )

    assert report.baseline.scan_id == a


async def test_a_target_with_one_run_has_nothing_to_compare(estate, now):
    b = await estate.scan("example.com", "only", at=now)

    with pytest.raises(HTTPException) as raised:
        await ScanCompareService(estate.session).comparison(None, b, estate.project_id)

    assert raised.value.status_code == 404


async def test_comparable_runs_explain_why_a_pair_is_refused(estate, now):
    old = now - timedelta(hours=2)
    await estate.scan("example.com", "census", at=old)
    await estate.scan(
        "example.com", "focused", at=now - timedelta(hours=1), scope="focused"
    )
    b = await estate.scan("example.com", "latest", at=now)

    runs = await ScanCompareService(estate.session).comparable(b, estate.project_id)

    by_name = {r.engine_name: r for r in runs}
    assert by_name["census"].comparable is True
    assert by_name["focused"].comparable is False
    assert "focused run" in by_name["focused"].reason


async def test_a_different_scan_context_is_a_run_difference(estate, now):
    old = now - timedelta(hours=2)
    a = await estate.scan("example.com", "first", at=old, engine=ENGINE)
    b = await estate.scan("example.com", "second", at=now, engine=ENGINE)
    first = await estate.session.get(Scan, a)
    second = await estate.session.get(Scan, b)
    first.context_name = "Unauthenticated"
    second.context_name = "Staff session"
    await estate.session.flush()

    report = await ScanCompareService(estate.session).comparison(
        a, b, estate.project_id
    )

    keys = {row.key: row for row in report.run_diff}
    assert keys["context"].baseline == "Unauthenticated"
    assert keys["context"].current == "Staff session"
    assert keys["context"].material is True
    assert report.comparability == Comparability.SETTINGS_DIFFER.value


async def test_intensity_and_scope_differences_are_named(estate, now):
    a, b, _ = await _pair(
        estate,
        now,
        config_a={"intensity": "normal", "excluded_subdomains": []},
        config_b={
            "intensity": "passive",
            "excluded_subdomains": ["staging.example.com"],
        },
    )

    report = await ScanCompareService(estate.session).comparison(
        a, b, estate.project_id
    )

    keys = {row.key: row for row in report.run_diff}
    assert keys["intensity"].current == "passive"
    assert keys["excluded_subdomains"].current == "staging.example.com"
    assert all(keys[k].material for k in ("intensity", "excluded_subdomains"))


async def test_a_proxy_is_reported_without_its_url(estate, now):
    a, b, _ = await _pair(
        estate,
        now,
        config_a={"proxy_url": None},
        config_b={"proxy_url": "http://user:secret@proxy.internal:8080"},
    )

    report = await ScanCompareService(estate.session).comparison(
        a, b, estate.project_id
    )

    proxy = next(row for row in report.run_diff if row.key == "proxy")
    assert (proxy.baseline, proxy.current) == ("none", "set")
    assert "secret" not in (proxy.current or "")


async def test_speed_settings_are_reported_but_not_material(estate, now):
    a, b, _ = await _pair(
        estate,
        now,
        config_a={"global_threads": 30},
        config_b={"global_threads": 60},
    )
    await estate.activity("first", RAN_WEB)
    await estate.activity("second", RAN_WEB)

    report = await ScanCompareService(estate.session).comparison(
        a, b, estate.project_id
    )

    threads = next(row for row in report.run_diff if row.key == "threads")
    assert threads.material is False
    assert report.comparability == Comparability.LIKE_FOR_LIKE.value


async def test_runs_in_between_are_counted(estate, now):
    a = await estate.scan(
        "example.com", "first", at=now - timedelta(hours=3), engine=ENGINE
    )
    await estate.scan(
        "example.com", "middle", at=now - timedelta(hours=2), engine=ENGINE
    )
    b = await estate.scan("example.com", "last", at=now, engine=ENGINE)

    report = await ScanCompareService(estate.session).comparison(
        a, b, estate.project_id
    )

    assert report.runs_between == 1


async def test_a_like_for_like_run_is_suggested(estate, now):
    twin = await estate.scan(
        "example.com", "twin", at=now - timedelta(hours=3), engine=ENGINE
    )
    odd = await estate.scan(
        "example.com",
        "odd",
        at=now - timedelta(hours=2),
        config={"intensity": "passive"},
        engine=ENGINE,
    )
    b = await estate.scan("example.com", "latest", at=now, engine=ENGINE)
    for name in ("twin", "odd", "latest"):
        await estate.activity(name, RAN_WEB)

    report = await ScanCompareService(estate.session).comparison(
        odd, b, estate.project_id
    )

    assert report.comparability == Comparability.SETTINGS_DIFFER.value
    assert report.suggestion is not None
    assert report.suggestion.scan_id == twin


async def test_a_cancelled_run_in_the_pair_lowers_the_verdict(estate, now):
    old = now - timedelta(hours=2)
    a = await estate.scan(
        "example.com", "first", at=old, status="cancelled", engine=ENGINE
    )
    b = await estate.scan("example.com", "second", at=now, engine=ENGINE)
    await estate.activity("first", RAN_WEB)
    await estate.activity("second", RAN_WEB)

    report = await ScanCompareService(estate.session).comparison(
        a, b, estate.project_id
    )

    assert report.comparability == Comparability.QUALITY_DIFFERS.value


async def test_the_refusal_wording_comes_from_the_definitions(estate, now):
    old = now - timedelta(hours=2)
    a = await estate.scan("one.example.com", "first", at=old)
    b = await estate.scan("two.example.com", "second", at=now)

    with pytest.raises(HTTPException) as raised:
        await ScanCompareService(estate.session).comparison(a, b, estate.project_id)

    assert raised.value.detail == REFUSAL_REASON[Refusal.DIFFERENT_TARGET.value]


async def test_empty_text_and_null_are_the_same_value(estate, now):
    a, b, old = await _pair(estate, now)
    await estate.hosts("first", ["a.example.com"], at=old, webserver="")
    await estate.hosts("second", ["a.example.com"], at=now, webserver=None)
    await estate.activity("first", RAN_WEB)
    await estate.activity("second", RAN_WEB)

    service = ScanCompareService(estate.session)
    report = await service.comparison(a, b, estate.project_id)
    rows = await service.rows(
        baseline_id=a,
        current_id=b,
        project_id=estate.project_id,
        dimension=WEB,
        verbs=[],
        page=1,
        size=50,
    )

    assert _dim(report, WEB).changed == 0
    assert rows.total == 0


async def test_a_counted_change_always_renders_a_field(estate, now):
    a, b, old = await _pair(estate, now)
    await estate.hosts(
        "first", ["a.example.com"], at=old, status=200, webserver="nginx"
    )
    await estate.hosts("second", ["a.example.com"], at=now, status=200, webserver="iis")
    await estate.activity("first", RAN_WEB)
    await estate.activity("second", RAN_WEB)

    service = ScanCompareService(estate.session)
    report = await service.comparison(a, b, estate.project_id)
    rows = await service.rows(
        baseline_id=a,
        current_id=b,
        project_id=estate.project_id,
        dimension=WEB,
        verbs=[ChangeVerb.CHANGED.value],
        page=1,
        size=50,
    )

    assert _dim(report, WEB).changed == rows.total == 1
    assert rows.items[0].verb == ChangeVerb.CHANGED.value
    assert rows.items[0].fields, "a counted change must name the field that moved"


async def test_rows_prove_coverage_when_the_rollup_columns_are_wrong(estate, now):
    old = now - timedelta(hours=2)
    a = await estate.scan(
        "example.com", "first", at=old, status="cancelled", engine=ENGINE
    )
    b = await estate.scan("example.com", "second", at=now, engine=ENGINE)
    await estate.hosts("first", ["gone.example.com", "kept.example.com"], at=old)
    await estate.hosts("second", ["kept.example.com"], at=now)
    await estate.activity("first", {"subdomain_discovery": "failed"})
    await estate.activity("second", RAN_WEB)

    report = await ScanCompareService(estate.session).comparison(
        a, b, estate.project_id
    )

    web = _dim(report, WEB)
    assert web.verdict.covered_baseline is True, "rows exist, so it was covered"
    assert web.total_baseline == 2
    assert web.disappeared == 1


async def test_service_pages_are_stable_across_a_shared_address(estate, now):
    a, b, old = await _pair(estate, now)
    ports = [("10.0.0.1", 8000 + n, "http") for n in range(12)]
    await estate.ports("first", [], at=old)
    await estate.ports("second", ports, at=now)
    await estate.activity("first", RAN_PORTS)
    await estate.activity("second", RAN_PORTS)

    service = ScanCompareService(estate.session)
    seen: list[str] = []
    for page in (1, 2, 3):
        result = await service.rows(
            baseline_id=a,
            current_id=b,
            project_id=estate.project_id,
            dimension=SERVICES,
            verbs=[],
            page=page,
            size=4,
        )
        seen += [row.key for row in result.items]

    assert len(seen) == len(set(seen)) == 12, "every port appears exactly once"


async def test_no_verbs_selected_returns_nothing(estate, now):
    a, b, old = await _pair(estate, now)
    await estate.hosts("first", ["gone.example.com"], at=old)
    await estate.hosts("second", ["new.example.com"], at=now)
    await estate.activity("first", RAN_WEB)
    await estate.activity("second", RAN_WEB)

    rows = await ScanCompareService(estate.session).rows(
        baseline_id=a,
        current_id=b,
        project_id=estate.project_id,
        dimension=WEB,
        verbs=[ChangeVerb.UNCONFIRMED.value],
        page=1,
        size=50,
    )

    assert rows.total == 0, "the only asked-for verb cannot occur here"
    assert rows.items == []


async def test_the_diff_reads_as_a_unified_diff(estate, now):
    a, b, old = await _pair(estate, now)
    await estate.hosts("first", ["gone.example.com", "kept.example.com"], at=old)
    await estate.hosts("second", ["kept.example.com", "new.example.com"], at=now)
    await estate.activity("first", RAN_WEB)
    await estate.activity("second", RAN_WEB)

    text = await ScanCompareService(estate.session).diff(
        baseline_id=a,
        current_id=b,
        project_id=estate.project_id,
        dimension=None,
        verbs=[],
    )

    lines = text.splitlines()
    assert lines[0].startswith("--- ")
    assert lines[1].startswith("+++ ")
    assert any(line.startswith("@@ web_assets") for line in lines)
    assert "+ new.example.com" in lines
    assert "- gone.example.com" in lines
    assert not any(line.startswith(" kept.example.com") for line in lines)


async def test_the_diff_names_a_dimension_one_run_did_not_scan(estate, now):
    a, b, old = await _pair(estate, now)
    await estate.vulns("first", [("cve-a", "high")], at=old)
    await estate.activity("first", RAN_VULNS)
    await estate.activity("second", RAN_WEB)

    text = await ScanCompareService(estate.session).diff(
        baseline_id=a,
        current_id=b,
        project_id=estate.project_id,
        dimension=None,
        verbs=[],
    )

    assert "# vulnerabilities  not scanned in the later run." in text
    assert "@@ vulnerabilities" not in text


async def test_the_diff_honours_the_dimension_and_verb_filters(estate, now):
    a, b, old = await _pair(estate, now)
    await estate.hosts("first", ["gone.example.com"], at=old)
    await estate.hosts("second", ["new.example.com"], at=now)
    await estate.ports("second", [("10.0.0.1", 22, "ssh")], at=now)
    await estate.activity("first", {**RAN_WEB, **RAN_PORTS})
    await estate.activity("second", {**RAN_WEB, **RAN_PORTS})

    text = await ScanCompareService(estate.session).diff(
        baseline_id=a,
        current_id=b,
        project_id=estate.project_id,
        dimension=WEB,
        verbs=[ChangeVerb.APPEARED.value],
    )

    assert "+ new.example.com" in text
    assert "gone.example.com" not in text
    assert "@@ services" not in text
