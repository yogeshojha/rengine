from __future__ import annotations

import threading
import time
import uuid
from types import SimpleNamespace

import pytest

from shared.definitions.intensity import Transport
from shared.definitions.scan_surface import ROOT_TIERS, Tier
from shared.definitions.vulnerabilities import Scanner
from shared.services.scan_surface import SurfaceItem, SurfacePlan, split
from stages.vulnerability_scan.config import VulnerabilityScanConfig
from stages.vulnerability_scan.scanners import nuclei as nuclei_scanner
from stages.vulnerability_scan.scanners.base import (
    Coverage,
    ScannerContext,
    ScannerResult,
)
from stages.vulnerability_scan.scanners.nuclei import (
    Job,
    NucleiScanner,
    _by_lane,
    _Templates,
)

pytestmark = pytest.mark.pipeline

STANDARD = "Standard rate"
REDUCED = "Reduced rate · WAF or CDN"


class _Writes:
    def __init__(self):
        self.threads: set[str] = set()
        self.stored: list = []
        self.marks: list = []

    def __call__(self, batch: list) -> int:
        self.threads.add(threading.current_thread().name)
        self.stored.extend(batch)
        return len(batch)

    def mark(self, ids, tier, status, batch) -> None:
        self.threads.add(threading.current_thread().name)
        self.marks.append((tier, status, batch, len(ids)))


def _item(value: str, guarded: bool = False, members: int = 0) -> SurfaceItem:
    item = SurfaceItem(
        id=uuid.uuid4(), class_="root", value=value, guarded=guarded, rank=1.0
    )
    item.members = [
        SurfaceItem(id=uuid.uuid4(), class_="root", value=f"{value}-{i}")
        for i in range(members)
    ]
    return item


def _scanner(writes: _Writes, **cfg) -> NucleiScanner:
    ctx = ScannerContext(
        session=None,
        scan_id=uuid.uuid4(),
        target_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        cfg=VulnerabilityScanConfig(**cfg),
        transport=Transport(tool="nuclei", rate=150, threads=25, timeout=10, retries=1),
        resolved=None,
        net=None,
        surface=SurfacePlan(),
        selection=None,
        on_findings=writes,
        on_marks=writes.mark,
    )
    return NucleiScanner(ctx)


def _job(lane: str, batch: int, tier: str = Tier.UNIVERSAL.value) -> Job:
    return Job(
        tier=tier,
        lane=lane,
        batch=batch,
        items=[_item(f"https://{lane[:1]}{batch}.example")],
        templates=["/t/x.yaml"],
        rate=10,
    )


def _library() -> _Templates:
    return _Templates(rows=[], paths={})


def _fake_one(hold: float, findings: int):
    def run(self, job, library, cap, store):
        coverage = Coverage(group=job.lane, tier=job.tier, batch=job.batch)
        deadline = time.monotonic() + hold
        sent = 0
        while sent < findings:
            store(coverage, [f"{job.lane}-{job.batch}-{sent}"])
            sent += 1
            time.sleep(hold / max(findings, 1))
        while time.monotonic() < deadline:
            time.sleep(0.01)
        return coverage

    return run


async def test_both_lanes_run_and_every_finding_is_stored(monkeypatch):
    writes = _Writes()
    scanner = _scanner(writes)
    monkeypatch.setattr(NucleiScanner, "_one", _fake_one(0.2, 5))
    result = ScannerResult()

    lanes = {STANDARD: [_job(STANDARD, 1)], REDUCED: [_job(REDUCED, 1)]}
    scanner._run_lanes(lanes, _library(), result)

    assert len(writes.stored) == 10
    assert result.findings == 10
    assert {c.group for c in result.coverage} == {STANDARD, REDUCED}
    assert {c.findings for c in result.coverage} == {5}


async def test_only_the_calling_thread_writes_findings_and_marks(monkeypatch):
    writes = _Writes()
    scanner = _scanner(writes)
    monkeypatch.setattr(NucleiScanner, "_one", _fake_one(0.2, 4))

    lanes = {STANDARD: [_job(STANDARD, 1)], REDUCED: [_job(REDUCED, 1)]}
    scanner._run_lanes(lanes, _library(), ScannerResult())

    assert writes.threads == {threading.current_thread().name}
    assert len(writes.marks) == 2


async def test_lanes_overlap_and_batches_within_a_lane_queue(monkeypatch):
    writes = _Writes()
    scanner = _scanner(writes)
    monkeypatch.setattr(NucleiScanner, "_one", _fake_one(0.3, 1))

    lanes = {
        STANDARD: [_job(STANDARD, 1), _job(STANDARD, 2)],
        REDUCED: [_job(REDUCED, 1), _job(REDUCED, 2)],
    }
    started = time.monotonic()
    scanner._run_lanes(lanes, _library(), ScannerResult())
    elapsed = time.monotonic() - started

    assert 0.55 < elapsed < 1.0, "two lanes of two 0.3s batches run side by side"


async def test_a_broken_lane_does_not_cost_the_other_its_coverage(monkeypatch):
    writes = _Writes()
    scanner = _scanner(writes)

    def run(self, job, library, cap, store):
        if job.lane == REDUCED:
            msg = "nuclei fell over"
            raise RuntimeError(msg)
        store(Coverage(group=job.lane), ["only-one"])
        return Coverage(group=job.lane, tier=job.tier, batch=job.batch)

    monkeypatch.setattr(NucleiScanner, "_one", run)
    outcome = ScannerResult()

    lanes = {STANDARD: [_job(STANDARD, 1)], REDUCED: [_job(REDUCED, 1)]}
    with pytest.raises(RuntimeError, match="fell over"):
        scanner._run_lanes(lanes, _library(), outcome)

    assert [c.group for c in outcome.coverage] == [STANDARD]
    assert writes.stored == ["only-one"]


async def test_the_budget_cuts_between_batches_and_marks_the_rest(monkeypatch):
    writes = _Writes()
    scanner = _scanner(writes)
    calls: list[int] = []

    def run(self, job, library, cap, store):
        calls.append(job.batch)
        scanner._deadline = time.monotonic()
        return Coverage(group=job.lane, tier=job.tier, batch=job.batch)

    monkeypatch.setattr(NucleiScanner, "_one", run)
    scanner._deadline = time.monotonic() + 600

    lanes = {STANDARD: [_job(STANDARD, 1), _job(STANDARD, 2), _job(STANDARD, 3)]}
    scanner._run_lanes(lanes, _library(), ScannerResult())

    assert calls == [1]
    statuses = [(batch, status) for _tier, status, batch, _n in writes.marks]
    assert statuses == [(1, "completed"), (2, "budget"), (3, "budget")]


def test_guarded_items_take_the_reduced_lane_only_with_a_divisor():
    items = [_item("https://a"), _item("https://b", guarded=True)]

    lanes = _by_lane(items, divisor=3)
    assert [i.value for i in lanes[STANDARD]] == ["https://a"]
    assert [i.value for i in lanes[REDUCED]] == ["https://b"]

    single = _by_lane(items, divisor=1)
    assert REDUCED not in single
    assert len(single[STANDARD]) == 2


def test_the_schedule_spends_the_budget_in_tier_order(monkeypatch):
    writes = _Writes()
    monkeypatch.setattr(nuclei_scanner, "WAF_RATE_DIVISOR", 1)
    scanner = _scanner(writes)
    rep = _item("https://rep.example", members=2)
    rep.tags = ["geoserver"]
    plan = SurfacePlan(roots=[rep])
    plan.services = [
        SurfaceItem(id=uuid.uuid4(), class_="service", value="rep.example:443")
    ]
    rows = [
        SimpleNamespace(
            id="r0",
            template_id="root",
            tags=["tech"],
            protocol="http",
            paths=["{{BaseURL}}"],
            simple=True,
            requests=1,
            origin="official",
        ),
        SimpleNamespace(
            id="r1",
            template_id="env",
            tags=["exposure"],
            protocol="http",
            paths=["{{BaseURL}}/.env", "{{BaseURL}}/app/.env"],
            simple=False,
            requests=1,
            origin="official",
        ),
        SimpleNamespace(
            id="r2",
            template_id="geo",
            tags=["cve", "geoserver"],
            protocol="http",
            paths=[],
            simple=False,
            requests=2,
            origin="official",
        ),
        SimpleNamespace(
            id="r3",
            template_id="blind",
            tags=["cve", "rce"],
            protocol="http",
            paths=[],
            simple=False,
            requests=2,
            origin="official",
        ),
        SimpleNamespace(
            id="r4",
            template_id="tls",
            tags=["ssl"],
            protocol="ssl",
            paths=[],
            simple=False,
            requests=1,
            origin="official",
        ),
    ]
    library = _Templates(
        rows=rows, paths={r.id: f"/t/{r.template_id}.yaml" for r in rows}
    )
    tiers = split(rows)
    lanes = scanner._schedule(plan, tiers, library, scanner._blind_budget(plan))

    jobs = lanes[STANDARD]
    assert [j.tier for j in jobs] == [
        Tier.ONE_REQUEST.value,
        Tier.UNIVERSAL.value,
        Tier.MATCHED.value,
        Tier.BLIND.value,
        Tier.SERVICES.value,
    ]
    assert len(jobs[0].items) == 3, "one-request runs on the members too, first"
    assert len(jobs[1].items) == 1, "universal runs on the representative"
    assert jobs[1].covered == 2
    assert jobs[2].templates == ["/t/geo.yaml"], "matched runs before the blind sweep"
    assert set(jobs[3].templates) == {"/t/geo.yaml", "/t/blind.yaml"}
    assert jobs[4].types == ("tcp", "ssl", "javascript")
    assert all(j.rate == 150 for j in jobs)


def test_the_deep_sweep_is_its_own_tier_and_never_planned(monkeypatch):
    writes = _Writes()
    monkeypatch.setattr(nuclei_scanner, "WAF_RATE_DIVISOR", 1)
    monkeypatch.setattr(nuclei_scanner, "blind_core", lambda rows, _budget=0: rows[:1])
    scanner = _scanner(writes)
    plan = SurfacePlan(roots=[_item("https://rep.example")])
    rows = [
        SimpleNamespace(
            id=f"r{i}",
            template_id=f"cve{i}",
            tags=["cve", f"product{i}"],
            protocol="http",
            paths=[],
            simple=False,
            requests=1,
            origin="official",
        )
        for i in range(2)
    ]
    library = _Templates(
        rows=rows, paths={r.id: f"/t/{r.template_id}.yaml" for r in rows}
    )
    tiers = split(rows)
    budget = scanner._blind_budget(plan)
    jobs = scanner._schedule(plan, tiers, library, budget)[STANDARD]
    assert [j.tier for j in jobs] == [Tier.BLIND.value]
    deep = scanner._schedule_deep(plan, tiers, library, budget)[STANDARD]
    assert [j.tier for j in deep] == [Tier.DEEP.value]
    assert deep[0].templates == ["/t/cve1.yaml"]
    assert Tier.DEEP.value not in ROOT_TIERS


def test_skipped_hosts_are_marked_alone_and_the_rest_complete():
    items = [
        SurfaceItem(
            id=uuid.uuid4(), class_="root", value="https://a", host="a", port=443
        ),
        SurfaceItem(
            id=uuid.uuid4(), class_="root", value="https://b", host="b", port=443
        ),
        SurfaceItem(
            id=uuid.uuid4(), class_="root", value="http://c:8080", host="c", port=8080
        ),
    ]
    job = Job(tier="blind", lane=STANDARD, batch=1, items=items, templates=[], rate=1)

    coverage = Coverage(group=STANDARD, tier="blind", batch=1)
    coverage.status = "partial"
    coverage.templates_loaded = 10
    coverage.hosts_dropped = [
        {"host": "b:443", "reason": "x"},
        {"host": "c:8080", "reason": "y"},
    ]
    dropped = nuclei_scanner._local_drops(coverage)
    assert dropped == {"b:443", "c:8080"}
    marks = nuclei_scanner._item_marks(job, coverage.status, dropped)
    assert [(len(i), s) for i, s in marks] == [(1, "completed"), (2, "partial")]
    assert marks[0][0][0].value == "https://a"
    unmatched = nuclei_scanner._item_marks(job, "partial", frozenset({"z:443"}))
    assert unmatched == [(items, "partial")]

    budget = Coverage(group=STANDARD, tier="blind", batch=1)
    budget.status = "partial"
    budget.templates_loaded = 10
    budget.error = "Stopped at the time budget. Remaining checks did not run."
    budget.hosts_dropped = list(coverage.hosts_dropped)
    assert nuclei_scanner._local_drops(budget) == frozenset()
    assert nuclei_scanner._item_marks(job, "partial", frozenset()) == [
        (items, "partial")
    ]


def test_the_scanner_is_registered_under_its_enum_name():
    assert NucleiScanner.name == Scanner.NUCLEI.value


def test_blind_and_deep_together_cover_every_product_check(monkeypatch):
    """A reduced blind budget must not strand checks between the blind core and deep."""
    monkeypatch.setattr(nuclei_scanner, "WAF_RATE_DIVISOR", 1)
    scanner = _scanner(_Writes())
    plan = SurfacePlan(roots=[_item("https://rep.example")])
    rows = [
        SimpleNamespace(
            id=f"p{i}",
            template_id=f"cve{i}",
            tags=["cve", f"product{i}"],
            protocol="http",
            paths=[],
            simple=False,
            requests=1,
            origin="official",
        )
        for i in range(6)
    ]
    library = _Templates(
        rows=rows, paths={r.id: f"/t/{r.template_id}.yaml" for r in rows}
    )
    tiers = split(rows)
    budget = 2  # smaller than the 6-check product tier
    blind = scanner._schedule(plan, tiers, library, budget)[STANDARD]
    deep = scanner._schedule_deep(plan, tiers, library, budget)[STANDARD]
    covered = {
        t for job in blind if job.tier == Tier.BLIND.value for t in job.templates
    }
    covered |= {t for job in deep for t in job.templates}
    assert covered == {f"/t/cve{i}.yaml" for i in range(6)}
