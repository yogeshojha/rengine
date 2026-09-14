from __future__ import annotations

import threading
import time
import uuid
from types import SimpleNamespace

import pytest

from shared.definitions.scan_surface import Tier
from shared.definitions.vulnerabilities import Scanner
from shared.services.scan_surface import SurfaceItem, SurfacePlan, split
from stages.vulnerability_scan.config import VulnerabilityScanConfig
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


def test_the_schedule_spends_the_budget_in_tier_order():
    writes = _Writes()
    scanner = _scanner(writes, waf_rate_divisor=1)
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
    lanes = scanner._schedule(plan, split(rows), library)

    jobs = lanes[STANDARD]
    assert [j.tier for j in jobs] == [
        Tier.ONE_REQUEST.value,
        Tier.UNIVERSAL.value,
        Tier.SERVICES.value,
        Tier.MATCHED.value,
        Tier.BLIND.value,
    ]
    assert len(jobs[0].items) == 3, "one-request runs on the members too"
    assert len(jobs[1].items) == 1, "universal runs on the representative"
    assert jobs[1].covered == 2
    assert jobs[2].types == ("tcp", "ssl", "javascript")
    assert jobs[3].templates == ["/t/geo.yaml"]
    assert set(jobs[4].templates) == {"/t/geo.yaml", "/t/blind.yaml"}
    assert all(j.rate == 150 for j in jobs)


def test_the_scanner_is_registered_under_its_enum_name():
    assert NucleiScanner.name == Scanner.NUCLEI.value
