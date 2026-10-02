from __future__ import annotations

import threading
import time
import uuid
from types import SimpleNamespace

import pytest

from shared.definitions.intensity import Transport
from shared.definitions.scan_surface import Tier
from shared.services.scan_surface import SurfaceItem, SurfacePlan
from stages.base import NetOptions
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
    _Seen,
    _spare_rate,
    _Templates,
)
from tools.nuclei.client import NucleiRun, NucleiStats, _drop_record

pytestmark = pytest.mark.pipeline

STANDARD = "Standard rate"
REDUCED = "Reduced rate · WAF or CDN"


def _skip_line(host: str) -> str:
    return (
        f"[INF] Skipped {host} from target list as found unresponsive "
        'permanently: cause="context deadline exceeded"'
    )


class _Marks:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, int | None, set[uuid.UUID]]] = []

    def __call__(self, ids, tier, status, batch) -> None:
        self.rows.append((tier, status, batch, set(ids)))

    def last(self, item: SurfaceItem, tier: str) -> tuple[str, int | None]:
        for row_tier, status, batch, ids in reversed(self.rows):
            if row_tier == tier and item.id in ids:
                return status, batch
        msg = f"{item.value} never marked"
        raise AssertionError(msg)


def _scanner(marks: _Marks | None = None, rate: int = 150) -> NucleiScanner:
    ctx = ScannerContext(
        session=None,
        scan_id=uuid.uuid4(),
        target_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        cfg=VulnerabilityScanConfig(),
        transport=Transport(
            tool="nuclei", rate=rate, threads=25, timeout=10, retries=1
        ),
        resolved=SimpleNamespace(follow_redirects=None, tool_args=lambda _tool: []),
        net=NetOptions(),
        surface=SurfacePlan(),
        selection=None,
        on_findings=lambda batch: len(batch),
        on_marks=marks,
    )
    return NucleiScanner(ctx)


def _root(name: str, members: int = 0) -> SurfaceItem:
    item = SurfaceItem(
        id=uuid.uuid4(),
        class_="root",
        value=f"https://{name}",
        host=name,
        port=443,
        scheme="https",
    )
    item.members = [
        SurfaceItem(id=uuid.uuid4(), class_="root", value=f"https://{i}.{name}")
        for i in range(members)
    ]
    return item


def _job(tier: str, batch: int, items: list[SurfaceItem], lane: str = STANDARD) -> Job:
    return Job(
        tier=tier,
        lane=lane,
        batch=batch,
        items=items,
        templates=[f"/t/{tier}.yaml"],
        rate=150,
    )


class _Nuclei:
    """Stands in for the nuclei binary: each run answers with its own stderr lines."""

    def __init__(self, stderr: list[list[str]]) -> None:
        self.stderr = list(stderr)
        self.runs: list[list[str]] = []

    def client(self, options=None, recorder=None):
        del options, recorder
        return self

    def scan(self, targets, **_kwargs) -> NucleiRun:
        self.runs.append(list(targets))
        lines = self.stderr.pop(0) if self.stderr else []
        run = NucleiRun()
        run.stats = NucleiStats(templates=4, hosts=len(targets), requests=8, total=8)
        run.dropped = [r for r in map(_drop_record, lines) if r is not None]
        run.duration_seconds = 1.0
        return run


def _lane_run(monkeypatch, jobs: list[Job], stderr: list[list[str]]):
    marks = _Marks()
    scanner = _scanner(marks)
    nuclei = _Nuclei(stderr)
    monkeypatch.setattr(nuclei_scanner, "NucleiClient", nuclei.client)
    result = ScannerResult()
    scanner._run_lanes({STANDARD: jobs}, _Templates(rows=[], paths={}), result)
    return result, marks, nuclei


# ---------- a skipped host is tried once more ----------


async def test_a_skipped_host_is_retried_after_the_tiers_last_batch(monkeypatch):
    a, b, c, d = (_root(f"{n}.example.com") for n in "abcd")
    s = _root("s.example.com")
    jobs = [
        _job(Tier.BLIND.value, 1, [a, b, c]),
        _job(Tier.BLIND.value, 2, [d]),
        _job(Tier.SERVICES.value, 3, [s]),
    ]
    result, marks, nuclei = _lane_run(
        monkeypatch, jobs, [[_skip_line("b.example.com:443")], [], [], []]
    )

    assert nuclei.runs == [
        [a.value, b.value, c.value],
        [d.value],
        [b.value],
        [s.value],
    ]
    first, _second, retry, _services = result.coverage
    assert (retry.tier, retry.batch, retry.status) == (Tier.BLIND.value, 4, "completed")
    assert retry.hosts_total == 1
    assert retry.error == "Retry of 1 target skipped after errors."
    assert first.status == "completed"
    assert first.hosts_dropped == []
    assert first.hosts_total == 2
    assert first.hosts_scanned == 2
    assert first.error == "1 target skipped after errors. Retried in batch 4."
    assert sum(row.hosts_total for row in result.coverage[:3]) == 4
    assert marks.last(b, Tier.BLIND.value) == ("completed", 4)
    assert marks.last(a, Tier.BLIND.value) == ("completed", 1)


async def test_a_host_skipped_twice_is_marked_partial_and_not_retried_again(
    monkeypatch,
):
    a, b = _root("a.example.com"), _root("b.example.com")
    skip = [_skip_line("b.example.com:443")]
    result, marks, nuclei = _lane_run(
        monkeypatch, [_job(Tier.UNIVERSAL.value, 1, [a, b])], [skip, skip]
    )

    assert nuclei.runs == [[a.value, b.value], [b.value]]
    first, retry = result.coverage
    assert retry.status == "partial"
    assert [d["host"] for d in retry.hosts_dropped] == ["b.example.com:443"]
    assert first.hosts_dropped == []
    dropped = {d["host"] for row in result.coverage for d in row.hosts_dropped}
    assert dropped == {"b.example.com:443"}
    assert marks.last(b, Tier.UNIVERSAL.value) == ("partial", 2)


async def test_skips_from_one_tier_share_a_single_retry(monkeypatch):
    a, b, c = (_root(f"{n}.example.com") for n in "abc")
    jobs = [
        _job(Tier.BLIND.value, 1, [a, b]),
        _job(Tier.BLIND.value, 2, [c]),
    ]
    result, _marks, nuclei = _lane_run(
        monkeypatch,
        jobs,
        [[_skip_line("a.example.com:443")], [_skip_line("c.example.com:443")], []],
    )

    assert nuclei.runs[2] == [a.value, c.value]
    assert len(nuclei.runs) == 3
    assert [row.error for row in result.coverage[:2]] == [
        "1 target skipped after errors. Retried in batch 3.",
        "1 target skipped after errors. Retried in batch 3.",
    ]
    assert [row.hosts_total for row in result.coverage] == [1, 0, 2]
    assert result.coverage[1].status == "completed"


async def test_another_check_set_gets_its_own_retry(monkeypatch):
    a, b = _root("a.example.com"), _root("b.example.com")
    first = _job(Tier.MATCHED.value, 1, [a])
    second = _job(Tier.MATCHED.value, 2, [b])
    second.templates = ["/t/other.yaml"]
    _result, _marks, nuclei = _lane_run(
        monkeypatch,
        [first, second],
        [[_skip_line("a.example.com:443")], [_skip_line("b.example.com:443")]],
    )
    assert nuclei.runs[2:] == [[a.value], [b.value]]


async def test_a_batch_cut_by_the_budget_is_not_retried(monkeypatch):
    a, b = _root("a.example.com"), _root("b.example.com")
    marks = _Marks()
    scanner = _scanner(marks)

    def one(self, job, library, cap, store):
        coverage = Coverage(group=job.lane, tier=job.tier, batch=job.batch)
        coverage.status = "partial"
        coverage.templates_loaded = 4
        coverage.hosts_dropped = [{"host": "b.example.com:443", "reason": "x"}]
        coverage.error = "Stopped at the time budget. Remaining checks did not run."
        return coverage

    monkeypatch.setattr(NucleiScanner, "_one", one)
    result = ScannerResult()
    scanner._run_lanes(
        {STANDARD: [_job(Tier.BLIND.value, 1, [a, b])]},
        _Templates(rows=[], paths={}),
        result,
    )
    assert len(result.coverage) == 1
    assert marks.last(b, Tier.BLIND.value) == ("partial", 1)


async def test_a_retry_the_budget_leaves_unrun_keeps_the_first_account(monkeypatch):
    a, b = _root("a.example.com"), _root("b.example.com")
    marks = _Marks()
    scanner = _scanner(marks)
    scanner._deadline = time.monotonic() + 600
    runs: list[int] = []

    def one(self, job, library, cap, store):
        runs.append(job.batch)
        scanner._deadline = time.monotonic()
        coverage = Coverage(group=job.lane, tier=job.tier, batch=job.batch)
        coverage.status = "partial"
        coverage.templates_loaded = 4
        coverage.hosts_total = len(job.items)
        coverage.hosts_dropped = [{"host": "b.example.com:443", "reason": "x"}]
        return coverage

    monkeypatch.setattr(NucleiScanner, "_one", one)
    result = ScannerResult()
    scanner._run_lanes(
        {STANDARD: [_job(Tier.BLIND.value, 1, [a, b])]},
        _Templates(rows=[], paths={}),
        result,
    )
    assert runs == [1]
    (first,) = result.coverage
    assert first.status == "partial"
    assert first.hosts_total == 2
    assert [d["host"] for d in first.hosts_dropped] == ["b.example.com:443"]
    assert first.error is None
    assert marks.last(b, Tier.BLIND.value) == ("partial", 1)


async def test_a_retry_moves_the_members_it_stands_for(monkeypatch):
    a, b = _root("a.example.com", members=2), _root("b.example.com", members=3)
    job = _job(Tier.MATCHED.value, 1, [a, b])
    result, _marks, _nuclei = _lane_run(
        monkeypatch, [job], [[_skip_line("b.example.com:443")], []]
    )
    first, retry = result.coverage
    assert (first.hosts_covered, retry.hosts_covered) == (2, 3)
    assert (first.hosts_total, retry.hosts_total) == (1, 1)


# ---------- each lane starts its deep sweep when its own core work is done ----------


def _timed(log: list, hold: dict[str, float]):
    def run(self, job, library, cap, store):
        started = time.monotonic()
        time.sleep(hold.get(f"{job.lane}:{job.tier}", 0.05))
        log.append((job.lane, job.tier, started, time.monotonic()))
        return Coverage(group=job.lane, tier=job.tier, batch=job.batch)

    return run


async def test_the_faster_lane_starts_its_deep_sweep_without_waiting(monkeypatch):
    log: list = []
    monkeypatch.setattr(
        NucleiScanner,
        "_one",
        _timed(log, {f"{STANDARD}:{Tier.BLIND.value}": 0.4}),
    )
    scanner = _scanner()
    core = {
        STANDARD: [_job(Tier.BLIND.value, 1, [_root("a.example.com")])],
        REDUCED: [_job(Tier.BLIND.value, 1, [_root("b.example.com")], REDUCED)],
    }
    deep = {
        STANDARD: [_job(Tier.DEEP.value, 1, [_root("a.example.com")])],
        REDUCED: [_job(Tier.DEEP.value, 1, [_root("b.example.com")], REDUCED)],
    }
    confirmed: list = []

    def confirm(held, between):
        between()
        confirmed.append((held, time.monotonic()))

    scanner._run_lanes(
        core, _Templates(rows=[], paths={}), ScannerResult(), deep=deep, confirm=confirm
    )

    at = {(lane, tier): (start, end) for lane, tier, start, end in log}
    standard_core_end = at[(STANDARD, Tier.BLIND.value)][1]
    assert at[(REDUCED, Tier.DEEP.value)][0] < standard_core_end
    assert [held for held, _ in confirmed] == [STANDARD]
    confirmed_at = confirmed[0][1]
    assert standard_core_end <= confirmed_at <= at[(STANDARD, Tier.DEEP.value)][0]


async def test_a_single_lane_confirms_before_its_deep_sweep(monkeypatch):
    log: list = []
    monkeypatch.setattr(NucleiScanner, "_one", _timed(log, {}))
    scanner = _scanner()
    order: list[str] = []

    def confirm(held, between):
        order.append(f"confirm:{held}")

    def one(self, job, library, cap, store):
        order.append(job.tier)
        return Coverage(group=job.lane, tier=job.tier, batch=job.batch)

    monkeypatch.setattr(NucleiScanner, "_one", one)
    scanner._run_lanes(
        {STANDARD: [_job(Tier.BLIND.value, 1, [_root("a.example.com")])]},
        _Templates(rows=[], paths={}),
        ScannerResult(),
        deep={STANDARD: [_job(Tier.DEEP.value, 1, [_root("a.example.com")])]},
        confirm=confirm,
    )
    assert order == [Tier.BLIND.value, f"confirm:{STANDARD}", Tier.DEEP.value]


async def test_a_failed_confirmation_stops_the_lanes(monkeypatch):
    started: list[str] = []

    def one(self, job, library, cap, store):
        started.append(f"{job.lane}:{job.tier}")
        if job.lane == REDUCED and job.tier == Tier.DEEP.value:
            deadline = time.monotonic() + 2
            while not self._stopping() and time.monotonic() < deadline:
                time.sleep(0.01)
        else:
            time.sleep(0.05 if job.lane == REDUCED else 0.3)
        return Coverage(group=job.lane, tier=job.tier, batch=job.batch)

    monkeypatch.setattr(NucleiScanner, "_one", one)
    scanner = _scanner()

    def confirm(held, between):
        msg = "confirmation broke"
        raise RuntimeError(msg)

    began = time.monotonic()
    with pytest.raises(RuntimeError, match="confirmation broke"):
        scanner._run_lanes(
            {
                STANDARD: [_job(Tier.BLIND.value, 1, [_root("a.example.com")])],
                REDUCED: [_job(Tier.BLIND.value, 1, [_root("b.example.com")], REDUCED)],
            },
            _Templates(rows=[], paths={}),
            ScannerResult(),
            deep={
                STANDARD: [_job(Tier.DEEP.value, 1, [_root("a.example.com")])],
                REDUCED: [
                    _job(Tier.DEEP.value, 1, [_root("b.example.com")], REDUCED),
                    _job(Tier.DEEP.value, 2, [_root("c.example.com")], REDUCED),
                ],
            },
            confirm=confirm,
        )
    assert time.monotonic() - began < 1.5, "the running deep batch is stopped"
    assert f"{STANDARD}:{Tier.DEEP.value}" not in started
    assert started.count(f"{REDUCED}:{Tier.DEEP.value}") == 1


def test_the_confirmation_spends_only_the_rate_the_deep_lanes_leave():
    rates = {STANDARD: 113, REDUCED: 37}
    deep = {STANDARD: [object()], REDUCED: [object()]}
    assert _spare_rate(150, rates, deep, STANDARD) == 113
    assert _spare_rate(150, rates, deep, REDUCED) == 37
    assert _spare_rate(150, rates, {STANDARD: [object()]}, STANDARD) == 150
    assert _spare_rate(150, rates, {}, STANDARD) == 150


async def test_replay_runs_under_the_ceiling_it_is_given(monkeypatch):
    rep = _root("rep.example.com", members=2)
    scanner = _scanner()
    rates: list[int] = []

    def one(self, job, library, cap, store):
        rates.append(job.rate)
        return Coverage(group=job.lane, tier=job.tier, batch=job.batch)

    monkeypatch.setattr(NucleiScanner, "_one", one)
    plan = SurfacePlan(roots=[rep])
    scanner._seen.append(
        _Seen(Tier.BLIND.value, "/t/x.yaml", "x", "fp", "https://rep.example.com/")
    )
    between = threading.Event()
    scanner._replay(
        plan, _Templates(rows=[], paths={}), ScannerResult(), 7, between.set
    )
    assert rates == [7]
    assert between.is_set()


async def test_a_run_replays_at_the_spare_rate_while_a_lane_is_in_deep(monkeypatch):
    rep = _root("rep.example.com", members=1)
    waf = _root("waf.example.com")
    waf.guarded = True
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
        for i in range(2)
    ]
    monkeypatch.setattr(NucleiScanner, "availability", lambda _self: (True, None))
    monkeypatch.setattr(nuclei_scanner, "selected_templates", lambda *_a: rows)
    monkeypatch.setattr(
        nuclei_scanner,
        "_resolve",
        lambda found: _Templates(
            rows=list(found), paths={r.id: f"/t/{r.template_id}.yaml" for r in found}
        ),
    )
    monkeypatch.setattr(nuclei_scanner, "blind_core", lambda product, _b: product[:1])
    log: list = []

    def one(self, job, library, cap, store):
        started = time.monotonic()
        slow = job.tier == Tier.BLIND.value and job.lane == REDUCED
        time.sleep(0.4 if slow else 0.05)
        if job.tier == Tier.BLIND.value and job.lane == STANDARD:
            self._seen.append(
                _Seen(Tier.BLIND.value, "/t/cve0.yaml", "cve0", "fp", f"{rep.value}/")
            )
        log.append((job.lane, job.tier, job.rate, started, time.monotonic()))
        return Coverage(group=job.lane, tier=job.tier, batch=job.batch)

    monkeypatch.setattr(NucleiScanner, "_one", one)
    scanner = _scanner()
    scanner.ctx.cfg = VulnerabilityScanConfig(store_evidence=False)
    scanner.ctx.surface = SurfacePlan(roots=[rep, waf])
    scanner.run()

    at = {(lane, tier): (rate, start, end) for lane, tier, rate, start, end in log}
    standard, reduced = nuclei_scanner._rate_plan(
        150, nuclei_scanner.WAF_RATE_DIVISOR, True
    )
    replay_rate, replay_start, _ = at[(STANDARD, Tier.REPLAY.value)]
    assert at[(STANDARD, Tier.DEEP.value)][1] < at[(REDUCED, Tier.BLIND.value)][2]
    assert replay_rate == reduced < standard
    assert at[(REDUCED, Tier.BLIND.value)][2] <= replay_start
    assert replay_start <= at[(REDUCED, Tier.DEEP.value)][1]
