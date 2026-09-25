from __future__ import annotations

from types import SimpleNamespace
from typing import ClassVar

import pytest
from sqlalchemy import select

from shared.definitions.ai_services import (
    AI_PORTS,
    MAX_MODELS,
    MCP_PATHS,
    SERVICES,
    AiCategory,
    normalise_category,
)
from shared.definitions.intensity import TransportTool, transport_for
from shared.definitions.ports import WEB_PORTS
from shared.definitions.tools import TOOL_NAMES
from shared.enums.target import TargetType
from shared.models.http_asset import HttpAsset
from shared.models.subdomain import Subdomain
from shared.services import ai_services
from shared.services.scan_resolve import ResolvedScanConfig
from stages.ai_detection import stage as ai_stage
from stages.ai_detection.stage import AiDetectionStage, _Pacer
from stages.base import StageContext
from tools.julius import AiMatch, JuliusOptions, JuliusRun, normalise_target
from tools.julius.client import STDIN_TARGETS, JuliusClient, parse_record

pytestmark = pytest.mark.pipeline


# ---------- client ----------


def test_a_bare_root_loses_its_trailing_slash_and_a_path_keeps_it():
    assert normalise_target("https://a.example:8443/") == "https://a.example:8443"
    assert normalise_target("https://a.example/mcp") == "https://a.example/mcp"
    assert (
        normalise_target("http://[2001:db8::1]:11434") == "http://[2001:db8::1]:11434"
    )


def test_a_record_folds_back_to_the_target_it_was_probed_as():
    match = parse_record(
        {
            "target": "http://10.0.0.5:11434/api/tags",
            "service": "Ollama",
            "matched_request": "/api/tags",
            "category": "self-hosted",
            "specificity": 100,
            "models": ["llama3:8b", ""],
        }
    )
    assert match is not None
    assert match.target == "http://10.0.0.5:11434"
    assert match.service == "ollama"
    assert match.models == ["llama3:8b"]


def test_an_mcp_record_on_an_exact_url_keeps_the_path():
    match = parse_record(
        {
            "target": "https://a.example/mcp",
            "service": "mcp-server",
            "matched_request": "",
            "category": "mcp",
            "specificity": 90,
        }
    )
    assert match.target == "https://a.example/mcp"


def test_a_record_without_a_service_is_dropped():
    assert parse_record({"target": "https://a.example"}) is None
    assert parse_record("not a record") is None


def _args(**over) -> list[str]:
    return JuliusClient.args(SimpleNamespace(options=JuliusOptions(**over)))


def test_the_client_asks_for_jsonl_and_carries_the_scan_headers():
    args = _args(headers={"Cookie": "a=b"}, concurrency=4, timeout=7)
    assert args[0] == "probe"
    assert args[args.index("-o") + 1] == "jsonl"
    assert args[args.index("-c") + 1] == "4"
    assert args[args.index("-t") + 1] == "7"
    assert args[args.index("-H") + 1] == "Cookie: a=b"
    assert "-p" not in args


def test_the_mcp_lane_loads_its_own_probe_directory():
    args = _args(probes_dir="/opt/julius/probes-mcp")
    assert args[args.index("-p") + 1] == "/opt/julius/probes-mcp"


def test_julius_takes_tool_args():
    assert "julius" in TOOL_NAMES


# ---------- vocabulary ----------


def test_every_ai_port_is_probed_for_http():
    assert set(AI_PORTS) <= set(WEB_PORTS)


def test_every_service_carries_a_known_category():
    assert {s.category for s in SERVICES} <= {c.value for c in AiCategory}
    assert len({s.key for s in SERVICES}) == len(SERVICES)


def test_an_unknown_service_takes_the_category_julius_reported():
    assert normalise_category("gateway", "new-gateway") == AiCategory.GATEWAY.value
    assert normalise_category("nonsense", "x") == AiCategory.GENERIC.value
    assert normalise_category("gateway", "ollama") == AiCategory.SELF_HOSTED.value


def test_julius_has_a_transport_row_at_every_intensity():
    for intensity in ("passive", "normal", "aggressive"):
        assert transport_for(TransportTool.JULIUS.value, intensity).threads >= 1


# ---------- verdicts ----------


def _d(service: str, specificity: int, models=()) -> ai_services.Detection:
    return ai_services.detection(service, None, specificity, "/", models)


def test_the_most_specific_service_wins_and_generic_comes_last():
    picked = ai_services.best(
        [_d("openai-compatible", 100, ["gpt-x"]), _d("litellm", 80), _d("vllm", 90)]
    )
    assert picked.service == "vllm"
    assert picked.models == ["gpt-x"]


def test_the_generic_shape_is_kept_when_nothing_else_matched():
    assert (
        ai_services.best([_d("openai-compatible", 10)]).service == "openai-compatible"
    )
    assert ai_services.best([]) is None


def test_model_lists_are_capped_deduplicated_and_scrubbed():
    found = ai_services.detection(
        "ollama", None, 100, "", ["a\x00b", "a\x00b", *[f"m{i}" for i in range(300)]]
    )
    assert found.models[0] == "ab"
    assert len(found.models) == MAX_MODELS
    assert found.endpoint == "/"


def test_the_pacer_spaces_starts_by_cost_over_rate():
    pacer = _Pacer(rate=100)
    assert pacer.wait_seconds() == 0
    pacer.spend(200)
    assert 1.5 < pacer.wait_seconds() <= 2.0
    free = _Pacer(rate=None)
    free.spend(10_000)
    assert free.wait_seconds() == 0


# ---------- the stage ----------


class _FakeJulius:
    calls: ClassVar[list[tuple[str | None, list[str]]]] = []

    def __init__(self, *, options, **_kw) -> None:
        self.options = options

    def probe(self, targets: list[str], **_kw) -> JuliusRun:
        _FakeJulius.calls.append((self.options.probes_dir, list(targets)))
        run = JuliusRun()
        for target in targets:
            if target == "http://ai.example.com:11434":
                run.matches[target] = [
                    AiMatch(target, "ollama", "self-hosted", 100, "/", ["llama3:8b"]),
                    AiMatch(target, "openai-compatible", "generic", 10, "/v1/models"),
                ]
            if target == "https://agent.example.com:443/mcp":
                run.matches[target] = [AiMatch(target, "mcp-server", "mcp", 90, "")]
            if target == "https://www.example.com:443/api/mcp":
                run.matches[target] = [
                    AiMatch(target, "ollama", "self-hosted", 100, "")
                ]
        return run


def _resolved(**stage) -> ResolvedScanConfig:
    return ResolvedScanConfig(
        target_value="example.com",
        target_type=TargetType.DOMAIN.value,
        stages={"ai_detection": stage},
    )


async def _seed(estate, now):
    await estate.scan("example.com", "run", at=now)
    names = [
        "ai.example.com",
        "agent.example.com",
        "www.example.com",
        "quiet.example.com",
    ]
    await estate.hosts("run", names, at=now, status=200)
    sid = estate.scans["run"]
    tid = estate.targets["example.com"]
    for host, scheme, port in [
        ("ai.example.com", "http", 11434),
        ("ai.example.com", "https", 443),
        ("agent.example.com", "https", 443),
        ("www.example.com", "https", 443),
    ]:
        estate.session.add(
            HttpAsset(
                project_id=estate.project_id,
                scan_id=sid,
                target_id=tid,
                url=f"{scheme}://{host}:{port}",
                host=host,
                port=port,
                scheme=scheme,
                status_code=200,
                discovered_at=now,
            )
        )
    await estate.session.flush()
    return sid, tid


def _run(estate, sid, tid, monkeypatch, **stage_cfg):
    monkeypatch.setattr(ai_stage, "JuliusClient", _FakeJulius)
    monkeypatch.setattr(AiDetectionStage, "publish_results", lambda *_: None)
    _FakeJulius.calls = []

    def go(sync_session):
        stage = AiDetectionStage(
            sync_session,
            StageContext(
                scan_id=sid,
                target_id=tid,
                project_id=estate.project_id,
                target_value="example.com",
                target_type=TargetType.DOMAIN.value,
                resolved=_resolved(**stage_cfg),
            ),
        )
        return stage.run()

    return estate.session.run_sync(go)


async def test_the_stage_writes_each_asset_and_folds_the_host(estate, now, monkeypatch):
    sid, tid = await _seed(estate, now)
    result = await _run(estate, sid, tid, monkeypatch)
    assert result.counts == {"probed": 4, "ai_services": 2}
    assert not result.partial

    assets = {
        (a.host, a.port): a
        for a in (
            await estate.session.execute(
                select(HttpAsset).where(HttpAsset.scan_id == sid)
            )
        ).scalars()
    }
    ollama = assets[("ai.example.com", 11434)]
    assert ollama.ai_checked is True
    assert ollama.ai_service == "ollama"
    assert ollama.ai_category == AiCategory.SELF_HOSTED.value
    assert ollama.ai_models == ["llama3:8b"]
    assert ollama.ai_endpoint == "/"
    mcp = assets[("agent.example.com", 443)]
    assert mcp.ai_service == "mcp-server"
    assert mcp.ai_endpoint == "/mcp"
    assert assets[("ai.example.com", 443)].ai_checked is True
    assert assets[("ai.example.com", 443)].ai_service is None
    assert assets[("www.example.com", 443)].ai_service is None

    hosts = dict(
        (
            await estate.session.execute(
                select(Subdomain.name, Subdomain.ai_services).where(
                    Subdomain.scan_id == sid
                )
            )
        ).all()
    )
    assert hosts["ai.example.com"] == ["ollama"]
    assert hosts["agent.example.com"] == ["mcp-server"]
    assert hosts["www.example.com"] == []
    assert hosts["quiet.example.com"] is None


async def test_the_ai_port_is_probed_first_and_mcp_paths_go_to_their_own_lane(
    estate, now, monkeypatch
):
    sid, tid = await _seed(estate, now)
    await _run(estate, sid, tid, monkeypatch)
    main, mcp = _FakeJulius.calls
    assert main[0] is None
    assert main[1][0] == "http://ai.example.com:11434"
    assert mcp[0] is not None
    assert set(mcp[1]) == {f"{root}{path}" for root in main[1] for path in MCP_PATHS}


async def test_mcp_paths_can_be_switched_off(estate, now, monkeypatch):
    sid, tid = await _seed(estate, now)
    result = await _run(estate, sid, tid, monkeypatch, mcp_paths=False)
    assert len(_FakeJulius.calls) == 1
    assert result.counts["ai_services"] == 1


async def test_the_budget_cap_is_reported_not_hidden(estate, now, monkeypatch):
    sid, tid = await _seed(estate, now)
    result = await _run(estate, sid, tid, monkeypatch, max_assets=1)
    assert result.partial
    assert result.counts["probed"] == 1
    assert any("3 web assets" in w for w in result.warnings)


async def test_a_batch_that_timed_out_marks_nothing_checked(estate, now, monkeypatch):
    sid, tid = await _seed(estate, now)

    class _Stuck(_FakeJulius):
        def probe(self, *_a, **_kw):
            return JuliusRun(timed_out=True, error="julius timed out")

    monkeypatch.setattr(ai_stage, "JuliusClient", _Stuck)
    monkeypatch.setattr(AiDetectionStage, "publish_results", lambda *_: None)

    def go(sync_session):
        return AiDetectionStage(
            sync_session,
            StageContext(
                scan_id=sid,
                target_id=tid,
                project_id=estate.project_id,
                target_value="example.com",
                target_type=TargetType.DOMAIN.value,
                resolved=_resolved(),
            ),
        ).run()

    result = await estate.session.run_sync(go)
    assert result.partial
    assert result.counts["probed"] == 0
    checked = (
        await estate.session.execute(
            select(HttpAsset.ai_checked).where(HttpAsset.scan_id == sid)
        )
    ).scalars()
    assert not any(checked)


def test_targets_are_read_from_stdin_not_a_file():
    assert STDIN_TARGETS == "-"
    assert "-f" not in _args()
