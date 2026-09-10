"""The execution plan must honour every depends_on, and defer only what is safe."""

from __future__ import annotations

import pytest

from stages.registry import execution_plan, ordered_levels, stages

pytestmark = pytest.mark.pipeline


def _specs():
    return {spec.name: spec for spec in stages()}


def _before(steps: list[tuple[str, ...]]) -> dict[str, set[str]]:
    """For each stage, everything that must finish before it may start."""
    out: dict[str, set[str]] = {}
    settled: set[str] = set()
    for step in steps:
        for name in step:
            out[name] = set(settled)
        settled |= set(step)
    return out


def test_the_plan_runs_every_stage_exactly_once():
    names = [name for step in execution_plan() for name in step]
    assert sorted(names) == sorted(_specs())
    assert len(names) == len(set(names)), "a stage must not be dispatched twice"


def test_every_dependency_completes_before_its_dependent_starts():
    before = _before(execution_plan())
    for name, spec in _specs().items():
        for dep in spec.depends_on:
            assert dep in before[name], f"{name} may start before {dep} has finished"


def test_a_producer_runs_before_anything_that_consumes_it():
    """depends_on is not the whole graph: asset_seed is named by nobody yet produces
    the hosts and addresses seven stages read."""
    specs = _specs()
    before = _before(execution_plan())
    for name, spec in specs.items():
        for other in specs.values():
            if other.name == name or not (other.consumes & spec.produces):
                continue
            assert name in before[other.name] or other.name in before[name], (
                f"{name} produces what {other.name} consumes but they run together"
            )


def test_vulnerability_scan_no_longer_holds_up_the_last_stages():
    """The whole point: it was 231 min of level 6 waiting on gov.ba."""
    plan = execution_plan()
    last = set(plan[-1])
    assert {"vulnerability_scan", "waf_detect"} <= last
    assert {"screenshot", "endpoint_probe", "ip_enrichment"} <= last, (
        "they must run alongside it, not after it"
    )
    before = _before(plan)
    for late in ("screenshot", "endpoint_probe", "ip_enrichment"):
        assert "vulnerability_scan" not in before[late]
    assert "origin_probe" in before["screenshot"]
    assert "url_discovery" in before["endpoint_probe"]


def test_a_stage_that_feeds_another_is_never_deferred():
    plan = execution_plan()
    assert "asset_seed" in plan[0], "it seeds the hosts every later stage reads"
    before = _before(plan)
    assert "asset_seed" in before["http_probe"]
    assert "netblock_sweep" in before["http_probe"]


def test_a_resumed_plan_omits_what_finished_and_keeps_the_order():
    done = frozenset({"seed_resolution", "subdomain_discovery", "host_discovery"})
    plan = execution_plan(done=done)
    before = _before(plan)
    assert not (done & set(before)), "a finished stage must not be dispatched again"
    for name, spec in _specs().items():
        if name in done:
            continue
        for dep in spec.depends_on - done:
            assert dep in before[name], f"{name} may start before {dep} on a resume"


def test_starting_mid_pipeline_still_orders_what_is_left():
    levels = ordered_levels()
    specs = _specs()
    for start in range(len(levels)):
        plan = execution_plan(start_level=start)
        before = _before(plan)
        remaining = {s.name for level in levels[start:] for s in level}
        for name in remaining:
            for dep in specs[name].depends_on & remaining:
                assert dep in before[name], f"level {start}: {name} precedes {dep}"


def test_an_exhausted_plan_is_empty():
    assert execution_plan(done=frozenset(_specs())) == []


def test_a_stage_that_sends_nothing_is_not_deferred():
    """target_enrichment fills the target's WHOIS and DNS in the first second;
    deferring it would hide them for the length of the scan and save nothing."""
    plan = execution_plan()
    assert "target_enrichment" in plan[0]
    assert "target_enrichment" not in plan[-1]


def test_the_deferred_stages_join_the_last_step_rather_than_follow_it():
    """A cheap stage left alone at the end would gate the very ones this defers."""
    plan = execution_plan()
    last = set(plan[-1])
    assert {"vulnerability_scan", "waf_detect", "ip_enrichment"} <= last
    assert len(plan) == len(ordered_levels()), "no extra step was appended"
