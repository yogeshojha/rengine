from __future__ import annotations

import dataclasses

import pytest
from fastapi import HTTPException

from app.services.target import TargetService
from app.services.target_enrichment import ENRICHMENTS, EnrichmentKind
from shared.enums.target import TargetType
from shared.enums.task_status import TaskStatus
from shared.models.target import Target

pytestmark = pytest.mark.api

UNPROCESSABLE = 422


def _recording(monkeypatch, service: TargetService) -> list[str]:
    """Replace every dispatcher and the activity log with a recorder of call order."""
    calls: list[str] = []
    for kind, enrichment in list(ENRICHMENTS.items()):
        monkeypatch.setitem(
            ENRICHMENTS,
            kind,
            dataclasses.replace(
                enrichment,
                dispatch=lambda ids, k=kind: calls.append(f"dispatch:{k}:{len(ids)}"),
            ),
        )
    original = service._activity.log_async

    async def log_async(**kwargs):
        calls.append("log")
        return await original(**kwargs)

    monkeypatch.setattr(service._activity, "log_async", log_async)
    return calls


@pytest.mark.parametrize("kind", list(EnrichmentKind))
async def test_a_refresh_logs_before_it_dispatches(estate, monkeypatch, kind):
    value = {
        EnrichmentKind.WHOIS: "example.com",
        EnrichmentKind.DNS: "example.com",
        EnrichmentKind.BGP: "AS13335",
    }[kind]
    target_type = TargetType.ASN if kind == EnrichmentKind.BGP else TargetType.DOMAIN
    target_id = await estate.target(value, target_type)
    service = TargetService(estate.session)
    calls = _recording(monkeypatch, service)

    response = await service.refresh_enrichment(str(target_id), kind)

    assert calls == ["log", f"dispatch:{kind}:1"]
    assert response.enrichment_type == kind.value
    target = await estate.session.get(Target, target_id)
    assert getattr(target, f"{kind.value}_status") == TaskStatus.PENDING


async def test_an_enrichment_that_does_not_apply_is_refused(estate, monkeypatch):
    target_id = await estate.target("example.com")
    service = TargetService(estate.session)
    calls = _recording(monkeypatch, service)
    with pytest.raises(HTTPException) as caught:
        await service.refresh_enrichment(str(target_id), EnrichmentKind.BGP)
    assert caught.value.status_code == UNPROCESSABLE
    assert caught.value.detail == (
        "BGP enrichment does not apply to domain targets. "
        "IP, IP range and ASN targets only."
    )
    assert calls == []


async def test_a_bulk_enrichment_queues_only_the_targets_it_applies_to(
    estate, monkeypatch
):
    domain = await estate.target("example.com")
    asn = await estate.target("AS13335", TargetType.ASN)
    service = TargetService(estate.session)
    calls = _recording(monkeypatch, service)

    assert await service.bulk_enrich([domain, asn], EnrichmentKind.DNS) == 1
    assert await service.bulk_enrich([domain, asn], EnrichmentKind.WHOIS) == 2
    assert calls == ["dispatch:dns:1", "dispatch:whois:2"]
