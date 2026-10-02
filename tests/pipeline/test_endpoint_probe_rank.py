from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from shared.definitions.intensity import Transport, transport_for
from shared.models.endpoint import Endpoint
from stages.endpoint_probe.config import (
    PROBE_SECONDS,
    EndpointProbeConfig,
    probe_budget,
)
from stages.endpoint_probe.stage import EndpointProbeStage

pytestmark = pytest.mark.pipeline


def _resolved() -> SimpleNamespace:
    return SimpleNamespace(excluded_paths=[], excluded_subdomains=[], excluded_ips=[])


async def _endpoints(estate, scan: str, rows: list[dict], at) -> None:
    sid = estate.scans[scan]
    target_id = await estate._target_of(sid)
    for row in rows:
        host = row["host"]
        path = row["path"]
        estate.session.add(
            Endpoint(
                project_id=estate.project_id,
                scan_id=sid,
                target_id=target_id,
                signature=uuid.uuid4().hex,
                family=row.get("family") or f"{host}|{path}",
                url=f"https://{host}{path}",
                host=host,
                path=path.split("?", 1)[0],
                dir_path="/",
                depth=row.get("depth", 1),
                param_count=row.get("params", 0),
                interest=row.get("interest", []),
                is_probed=row.get("seen", False),
                endpoint_class="page",
                discovered_at=at,
            )
        )
    await estate.session.flush()


async def _pending(estate, scan: str, budget: int) -> list[str]:
    def run(sync_session) -> list[str]:
        stage = EndpointProbeStage.__new__(EndpointProbeStage)
        stage.session = sync_session
        stage.ctx = SimpleNamespace(scan_id=estate.scans[scan], resolved=_resolved())
        stage.cfg = EndpointProbeConfig()
        return stage._pending(budget)

    return await estate.session.run_sync(run)


async def test_hosts_take_turns_instead_of_the_first_host_by_name(estate, now):
    await estate.scan("example.com", "run", at=now)
    await _endpoints(
        estate,
        "run",
        [
            *(
                {"host": "a.example.com", "path": f"/p{i}?id=1", "params": 1}
                for i in range(6)
            ),
            *(
                {"host": "b.example.com", "path": f"/q{i}?id=1", "params": 1}
                for i in range(2)
            ),
            {"host": "c.example.com", "path": "/r?id=1", "params": 1},
        ],
        now,
    )
    picked = await _pending(estate, "run", 6)
    assert picked == [
        "https://a.example.com/p0?id=1",
        "https://b.example.com/q0?id=1",
        "https://c.example.com/r?id=1",
        "https://a.example.com/p1?id=1",
        "https://b.example.com/q1?id=1",
        "https://a.example.com/p2?id=1",
    ]


async def test_new_families_and_parameters_lead_the_budget(estate, now):
    await estate.scan("example.com", "run", at=now)
    await _endpoints(
        estate,
        "run",
        [
            {"host": "a.example.com", "path": "/item?id=1", "params": 1, "family": "f"},
            {"host": "a.example.com", "path": "/item?id=2", "params": 1, "family": "f"},
            {"host": "a.example.com", "path": "/item?id=3", "params": 1, "family": "f"},
            {"host": "a.example.com", "path": "/about", "family": "g"},
            {
                "host": "a.example.com",
                "path": "/search?q=x",
                "params": 1,
                "family": "h",
            },
            {"host": "a.example.com", "path": "/seen?x=1", "params": 1, "seen": True},
        ],
        now,
    )
    picked = await _pending(estate, "run", 6)
    assert picked == [
        "https://a.example.com/item?id=1",
        "https://a.example.com/search?q=x",
        "https://a.example.com/about",
        "https://a.example.com/item?id=2",
        "https://a.example.com/item?id=3",
        "https://a.example.com/seen?x=1",
    ]


async def test_a_flagged_endpoint_leads_its_host_turn(estate, now):
    await estate.scan("example.com", "run", at=now)
    await _endpoints(
        estate,
        "run",
        [
            {"host": "a.example.com", "path": "/a"},
            {"host": "a.example.com", "path": "/zz-admin", "interest": ["admin"]},
            {"host": "b.example.com", "path": "/b"},
        ],
        now,
    )
    picked = await _pending(estate, "run", 2)
    assert picked == ["https://a.example.com/zz-admin", "https://b.example.com/b"]


def test_the_automatic_budget_is_thirty_minutes_at_the_stage_rate():
    normal = EndpointProbeStage.default_transport("normal")
    assert probe_budget(normal) == min(normal.rate, normal.threads) * PROBE_SECONDS
    slow = Transport(tool="httpx", rate=5, threads=40, timeout=10, retries=0)
    assert probe_budget(slow) == 5 * PROBE_SECONDS
    capped = transport_for(
        "httpx", "aggressive", thread_weight=EndpointProbeStage.thread_weight, ceiling=2
    )
    assert probe_budget(capped) == 2 * PROBE_SECONDS


def test_an_explicit_budget_wins_and_zero_means_automatic():
    assert EndpointProbeConfig().max_urls == 0
    assert EndpointProbeConfig(max_urls=300).max_urls == 300
