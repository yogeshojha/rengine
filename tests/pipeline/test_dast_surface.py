from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from shared.definitions.scan_surface import Tier
from shared.services.scan_surface import SurfaceItem, SurfacePlan, by_origin
from shared.services.scan_surface.requests import _better, _rewrite
from stages.dast_scan.config import DastScanConfig
from stages.dast_scan.scanners import scanners
from stages.dast_scan.scanners.nuclei import NucleiDastScanner
from stages.registry import execution_plan, stage_by_name
from stages.vulnerability_scan.scanners.base import ScannerContext
from stages.vulnerability_scan.scanners.nuclei import Job, _Templates

pytestmark = pytest.mark.pipeline


def _before(steps: list[tuple[str, ...]]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    settled: set[str] = set()
    for step in steps:
        for name in step:
            out[name] = set(settled)
        settled |= set(step)
    return out


def _item(value: str, asset: uuid.UUID, cls: str = "request", rank: float = 1.0):
    return SurfaceItem(
        id=uuid.uuid4(), class_=cls, value=value, asset_id=asset, rank=rank
    )


def _scanner(**cfg) -> NucleiDastScanner:
    ctx = ScannerContext(
        session=None,
        scan_id=uuid.uuid4(),
        target_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        cfg=DastScanConfig(**cfg),
        resolved=None,
        net=None,
        surface=SurfacePlan(),
        selection=None,
    )
    return NucleiDastScanner(ctx)


def test_the_fuzzing_stage_runs_after_the_probe_and_the_scanner():
    spec = stage_by_name()["dast_scan"]
    before = _before(execution_plan())["dast_scan"]

    assert "endpoints" in spec.consumes
    assert "endpoint_probe" in before
    assert "vulnerability_scan" in before
    assert DastScanConfig().enabled is False


def test_the_fuzzers_are_discovered_by_module():
    assert "nuclei" in scanners()


def test_a_request_is_rewritten_onto_its_origin():
    assert (
        _rewrite("https://rep.example", "https://member.example:443/a/b?id=1&x=2")
        == "https://rep.example/a/b?id=1&x=2"
    )
    assert _rewrite("http://rep.example:8080", "http://m.example:8080/") == (
        "http://rep.example:8080/"
    )


def test_the_answering_richer_shorter_endpoint_represents_its_parameter_set():
    ok = SimpleNamespace(status_code=200, variants=3, url="https://a/x?id=1")
    long = SimpleNamespace(status_code=200, variants=3, url="https://a/x?id=1&utm=z")
    dead = SimpleNamespace(status_code=500, variants=9, url="https://a/x?id=2")
    assert _better(ok, None)
    assert _better(ok, long)
    assert not _better(long, ok)
    assert _better(ok, dead)


def test_items_are_grouped_per_origin_in_rank_order():
    a, b = uuid.uuid4(), uuid.uuid4()
    items = [
        _item("https://b/1", b, rank=1),
        _item("https://a/1", a, rank=5),
        _item("https://b/2", b, rank=1),
    ]
    groups = by_origin(items)
    assert [len(g) for g in groups] == [1, 2]
    assert groups[0][0].value == "https://a/1"


def test_the_schedule_fuzzes_requests_and_probes_directories(monkeypatch):
    scanner = _scanner(waf_rate_divisor=1, directories=True)
    origin = uuid.uuid4()
    plan = SurfacePlan(
        requests=[_item(f"https://a/p?id={i}", origin) for i in range(3)],
        bases=[_item("https://a/app/", origin, cls="base")],
    )
    fuzz_rows = [
        SimpleNamespace(
            id="f1",
            template_id="sqli",
            tags=["dast"],
            protocol="http",
            paths=[],
            simple=False,
            requests=1,
        )
    ]
    exposure_rows = [
        SimpleNamespace(
            id="e1",
            template_id="env",
            tags=["exposure"],
            protocol="http",
            paths=["{{BaseURL}}/.env"],
            simple=True,
            requests=1,
        )
    ]
    fuzz = _Templates(rows=fuzz_rows, paths={"f1": "/t/dast/sqli.yaml"})
    exposure = _Templates(rows=exposure_rows, paths={"e1": "/t/env.yaml"})

    lanes = scanner._schedule_requests(plan, fuzz, exposure)

    jobs = lanes["Standard rate"]
    assert [j.tier for j in jobs] == [Tier.DAST.value, Tier.BASES.value]
    assert jobs[0].dast is True
    assert jobs[0].templates == ["/t/dast/sqli.yaml"]
    assert len(jobs[0].items) == 3
    assert jobs[1].dast is False
    assert jobs[1].targets == ["https://a/app/"]


def test_a_fuzzing_finding_replays_the_same_request_on_each_equivalent():
    scanner = _scanner()
    rep = uuid.uuid4()
    member = SurfaceItem(id=uuid.uuid4(), class_="root", value="https://m.example")
    plan = SurfacePlan(equivalents={"https://rep.example": [member]})
    finding = SimpleNamespace(
        url="https://rep.example/search?q=1",
        matched_at="https://rep.example/search?q=1",
    )

    targets = scanner._replay_targets(plan, finding)

    assert targets == [(member, "https://m.example/search?q=1")]
    _ = rep


def test_a_fuzzing_job_passes_dast_and_the_parameter_patience():
    scanner = _scanner(fuzz_param_frequency=7)
    scanner.ctx.net = SimpleNamespace(proxy_url=None, headers={})
    scanner.ctx.resolved = SimpleNamespace(
        follow_redirects=None, tool_args=lambda _t: [], excluded_subdomains=[]
    )
    job = Job(
        tier=Tier.DAST.value,
        lane="Standard rate",
        batch=1,
        items=[],
        templates=[],
        rate=5,
        dast=True,
    )
    options = scanner._options(job, Path("t.txt"), None)

    assert options.dast is True
    assert options.fuzz_param_frequency == 7
