from __future__ import annotations

import pytest
from sqlalchemy import update

from app.services.port import PortService
from app.services.subdomain import SubdomainService
from shared.models.http_asset import HttpAsset
from shared.models.scan_correlation import ServiceFilter
from shared.models.subdomain import SubdomainFilter
from shared.services.ai_services import _FOLD_SQL

pytestmark = pytest.mark.grammar


async def _seed(estate, now):
    await estate.scan("example.com", "run", at=now)
    names = [
        "ollama.example.com",
        "gw.example.com",
        "mcp.example.com",
        "plain.example.com",
        "unchecked.example.com",
    ]
    await estate.hosts("run", names, at=now, status=200)
    for i, name in enumerate(names):
        await estate.assets("run", [name], at=now, ip=f"203.0.113.{i + 1}")
    await estate.ports(
        "run", [(f"203.0.113.{i + 1}", 443, "https") for i in range(len(names))], at=now
    )
    sid = estate.scans["run"]
    rows = {
        "ollama.example.com": ("ollama", "self_hosted", ["llama3:8b", "qwen2.5"]),
        "gw.example.com": ("litellm", "gateway", ["gpt-4o"]),
        "mcp.example.com": ("mcp-server", "mcp", None),
        "plain.example.com": (None, None, None),
    }
    for host, (service, category, models) in rows.items():
        await estate.session.execute(
            update(HttpAsset)
            .where(HttpAsset.scan_id == sid, HttpAsset.host == host)
            .values(
                ai_checked=True,
                ai_service=service,
                ai_category=category,
                ai_models=models,
            )
        )
    await estate.session.execute(_FOLD_SQL, {"scan_id": sid, "hosts": None})
    await estate.session.flush()
    return sid


async def _count(service, project_id, sid, q: str) -> int:
    result = await service.search(
        project_id=project_id, scope=sid, f=SubdomainFilter(q=q, limit=50)
    )
    assert result.error is None, result.error
    return result.total


async def test_ai_filters_match_the_rows_they_promise(estate, session, now):
    sid = await _seed(estate, now)
    service = SubdomainService(session)
    pid = estate.project_id
    assert await _count(service, pid, sid, "ai:yes") == 3
    assert await _count(service, pid, sid, "ai:no") == 2
    assert await _count(service, pid, sid, "ai:ollama") == 1
    assert await _count(service, pid, sid, "ai:Ollama") == 1
    assert await _count(service, pid, sid, "ai:[ollama,litellm]") == 2
    assert await _count(service, pid, sid, "ai:gateway") == 1
    assert await _count(service, pid, sid, "ai:mcp") == 1
    assert await _count(service, pid, sid, "not ai:ollama") == 4
    assert await _count(service, pid, sid, "ai.model:yes") == 2
    assert await _count(service, pid, sid, 'ai.model:"llama3:8b"') == 1
    assert await _count(service, pid, sid, "ai.model~qwen") == 1


async def test_the_host_row_carries_the_services(estate, session, now):
    sid = await _seed(estate, now)
    result = await SubdomainService(session).search(
        project_id=estate.project_id,
        scope=sid,
        f=SubdomainFilter(q="ai:yes", limit=50, sort="name"),
    )
    by_name = {r.name: r.ai_services for r in result.items}
    assert by_name["ollama.example.com"] == ["ollama"]


async def _services(service, sid, q: str) -> int:
    page = await service.search(sid, ServiceFilter(q=q, limit=50))
    assert page.error is None, page.error
    return page.total


async def test_services_carry_the_ai_their_web_assets_answered_with(
    estate, session, now
):
    sid = await _seed(estate, now)
    service = PortService(session)
    assert await _services(service, sid, "ai:yes") == 3
    assert await _services(service, sid, "ai:no") == 2
    assert await _services(service, sid, "ai:ollama") == 1
    assert await _services(service, sid, "ai:gateway") == 1
    assert await _services(service, sid, "ai.model:yes") == 2
    assert await _services(service, sid, 'ai.model:"llama3:8b"') == 1
    page = await service.search(sid, ServiceFilter(q="ai:ollama", limit=5))
    assert page.items[0].ai_services == ["ollama"]
    assert page.items[0].ai_models == ["llama3:8b", "qwen2.5"]


async def test_the_summary_counts_equal_the_filters(estate, session, now):
    sid = await _seed(estate, now)
    service = PortService(session)
    summary = await service.ai(sid)
    assert summary.evaluated == 4
    assert summary.found == 3
    assert summary.models_listed == 2
    assert {s.key for s in summary.services} == {"ollama", "litellm", "mcp-server"}
    for entry in summary.services:
        assert await _services(service, sid, entry.query) == entry.count
    for entry in summary.models:
        assert await _services(service, sid, entry.query) == entry.count
    assert {m.name for m in summary.models} == {"llama3:8b", "qwen2.5", "gpt-4o"}
