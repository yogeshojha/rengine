"""The execution plan must honour every depends_on and gate on nothing else."""

from __future__ import annotations

import pytest

from stages.registry import StagePlan, execution_plan, ordered_levels, stages

pytestmark = pytest.mark.pipeline


def _before(plan: StagePlan | None) -> dict[str, set[str]]:
    """For each stage, everything that must finish before it may start."""
    out: dict[str, set[str]] = {}
    settled: set[str] = set()
    while plan is not None:
        for name in (*plan.gating, *plan.beside):
            out[name] = set(settled)
        # only the gating half holds the next step up
        settled |= set(plan.gating)
        plan = plan.then
    return out


def _all_stages() -> dict[str, frozenset[str]]:
    return {spec.name: spec.depends_on for spec in stages()}


def test_the_plan_runs_every_stage_exactly_once():
    plan = execution_plan()
    assert plan is not None
    names: list[str] = []
    step: StagePlan | None = plan
    while step is not None:
        names.extend((*step.gating, *step.beside))
        step = step.then
    assert sorted(names) == sorted(_all_stages())
    assert len(names) == len(set(names)), "a stage must not be dispatched twice"


def test_every_dependency_completes_before_its_dependent_starts():
    before = _before(execution_plan())
    for name, deps in _all_stages().items():
        for dep in deps:
            assert dep in before[name], f"{name} may start before {dep} has finished"


def test_a_stage_nothing_depends_on_never_gates_the_next_step():
    """The whole point: level 6 waited hours on vulnerability_scan, which nothing reads."""
    awaited = {dep for deps in _all_stages().values() for dep in deps}
    step: StagePlan | None = execution_plan()
    while step is not None:
        for name in step.gating:
            assert name in awaited or step.then is None, (
                f"{name} gates the next step but nothing depends on it"
            )
        for name in step.beside:
            assert name not in awaited, (
                f"{name} runs beside the spine but is depended on"
            )
        step = step.then


def test_vulnerability_scan_does_not_hold_up_the_last_level():
    before = _before(execution_plan())
    for late in ("screenshot", "endpoint_probe", "ip_enrichment"):
        assert "vulnerability_scan" not in before[late]
        assert "waf_detect" not in before[late]
    # and the ones it genuinely needs are still in front of it
    assert "origin_probe" in before["screenshot"]
    assert "url_discovery" in before["endpoint_probe"]
    assert "service_fingerprint" in before["ip_enrichment"]


def test_target_enrichment_never_gates_the_scan():
    """CLAUDE.md has claimed this for a while; the level flattening made it false."""
    before = _before(execution_plan())
    assert "target_enrichment" not in before["host_discovery"]
    assert "asset_seed" not in before["host_discovery"]


def test_a_resumed_plan_omits_what_finished_and_keeps_the_order():
    done = frozenset({"seed_resolution", "subdomain_discovery", "host_discovery"})
    plan = execution_plan(done=done)
    assert plan is not None
    before = _before(plan)
    assert not (done & set(before)), "a finished stage must not be dispatched again"
    for name, deps in _all_stages().items():
        if name in done:
            continue
        for dep in deps - done:
            assert dep in before[name], f"{name} may start before {dep} on a resume"


def test_starting_mid_pipeline_still_orders_what_is_left():
    levels = ordered_levels()
    for start in range(len(levels)):
        plan = execution_plan(start_level=start)
        if plan is None:
            continue
        before = _before(plan)
        remaining = {n for level in levels[start:] for n in (s.name for s in level)}
        for name in remaining:
            for dep in _all_stages()[name] & remaining:
                assert dep in before[name], f"level {start}: {name} precedes {dep}"
