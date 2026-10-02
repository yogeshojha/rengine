from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select

import app.services.vulnerability as vulnerability_service
from app.services.note import NoteService
from app.services.vulnerability import VulnerabilityService
from mcp import server, telemetry
from mcp.capabilities import Capability
from mcp.context import TokenIdentity, ToolContext
from mcp.errors import InvalidParamsError, ToolError
from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import VulnState
from shared.models.note import Note, NoteCreate
from shared.models.vulnerability import (
    BulkTriageUpdate,
    TriageUpdate,
    VulnerabilityFilter,
)

pytestmark = pytest.mark.api

CONFIRMED = VulnState.CONFIRMED.value
FALSE_POSITIVE = VulnState.FALSE_POSITIVE.value


async def _reasons(estate) -> list[tuple[str, str | None]]:
    rows = await estate.session.execute(
        select(Note.body, Note.triage_state)
        .where(Note.project_id == estate.project_id)
        .order_by(Note.created_at)
    )
    return [tuple(r) for r in rows.all()]


async def _row(estate, sid, fingerprint: str = "rce"):
    page = await VulnerabilityService(estate.session).search(
        sid, VulnerabilityFilter(include_suppressed=True)
    )
    return next(v for v in page.items if v.fingerprint == fingerprint)


async def _finding(estate, now):
    sid = await estate.scan("example.com", "run", at=now)
    await estate.vulns("run", [("rce", "critical"), ("xss", "high")], at=now)
    await estate.session.commit()
    return sid


async def test_a_reason_is_a_note_on_the_finding(durable_estate, now):
    estate = durable_estate
    sid = await _finding(estate, now)
    service = VulnerabilityService(estate.session)

    result = await service.triage(
        sid,
        "rce",
        TriageUpdate(state=FALSE_POSITIVE, reason="WAF strips the payload"),
        estate.user_id,
    )
    assert result.reason == "WAF strips the payload"
    assert await _reasons(estate) == [("WAF strips the payload", FALSE_POSITIVE)]
    note = await estate.session.scalar(select(Note))
    assert note.dimension == SurfaceDimension.VULNERABILITIES.value
    assert note.asset_key == "rce"
    assert note.scan_id == sid
    assert note.asset_label == "Rce on www.example.com"

    row = await _row(estate, sid)
    assert row.state == FALSE_POSITIVE
    assert row.reason == "WAF strips the payload"
    assert row.reason_by == f"t{estate.user_id.hex[:8]}"
    assert row.reason_at is not None


async def test_the_reason_follows_the_current_state(durable_estate, now):
    estate = durable_estate
    sid = await _finding(estate, now)
    service = VulnerabilityService(estate.session)

    await service.triage(
        sid,
        "rce",
        TriageUpdate(state=FALSE_POSITIVE, reason="Static page"),
        estate.user_id,
    )
    reopened = await service.triage(
        sid, "rce", TriageUpdate(state=VulnState.OPEN.value), estate.user_id
    )
    assert reopened.reason is None
    assert (await _row(estate, sid)).reason is None

    confirmed = await service.triage(
        sid, "rce", TriageUpdate(state=CONFIRMED), estate.user_id
    )
    assert confirmed.reason is None

    again = await service.triage(
        sid, "rce", TriageUpdate(state=FALSE_POSITIVE), estate.user_id
    )
    assert again.reason == "Static page"
    assert (await _row(estate, sid)).reason == "Static page"
    assert (await _row(estate, sid, "xss")).reason is None


async def test_a_note_saved_with_a_triage_state_is_the_reason(durable_estate, now):
    estate = durable_estate
    sid = await _finding(estate, now)
    await VulnerabilityService(estate.session).triage(
        sid, "rce", TriageUpdate(state=CONFIRMED), estate.user_id
    )
    notes = NoteService(estate.session)
    anchor = {
        "target_id": estate.targets["example.com"],
        "scan_id": sid,
        "dimension": SurfaceDimension.VULNERABILITIES.value,
        "asset_key": "rce",
    }
    await notes.create(
        NoteCreate(**anchor, body="Seen in prod", triage_state=CONFIRMED),
        estate.project_id,
        estate.user_id,
    )
    await notes.create(
        NoteCreate(**anchor, body="Plain note on the finding"),
        estate.project_id,
        estate.user_id,
    )
    assert (await _row(estate, sid)).reason == "Seen in prod"


async def test_bulk_triage_writes_one_reason_per_finding(durable_estate, now):
    estate = durable_estate
    sid = await _finding(estate, now)
    result = await VulnerabilityService(estate.session).triage_many(
        sid,
        BulkTriageUpdate(
            fingerprints=["rce", "xss"], state=FALSE_POSITIVE, reason="Test host"
        ),
        estate.user_id,
    )
    assert result.reasons == 2
    assert await _reasons(estate) == [
        ("Test host", FALSE_POSITIVE),
        ("Test host", FALSE_POSITIVE),
    ]
    assert (await _row(estate, sid, "xss")).reason == "Test host"

    plain = await VulnerabilityService(estate.session).triage_many(
        sid, BulkTriageUpdate(fingerprints=["rce"], state=CONFIRMED), estate.user_id
    )
    assert plain.reasons == 0


async def test_bulk_reason_is_refused_over_the_selection_cap(
    durable_estate, now, monkeypatch
):
    estate = durable_estate
    sid = await _finding(estate, now)
    monkeypatch.setattr(vulnerability_service, "MAX_SELECTED_ROWS", 1)
    with pytest.raises(HTTPException) as refused:
        await VulnerabilityService(estate.session).triage_many(
            sid,
            BulkTriageUpdate(
                fingerprints=["rce", "xss"], state=FALSE_POSITIVE, reason="Test host"
            ),
            estate.user_id,
        )
    assert refused.value.status_code == 422
    assert await _reasons(estate) == []
    assert (await _row(estate, sid)).state == VulnState.OPEN.value


async def test_a_reason_needs_a_review_state():
    with pytest.raises(ValidationError):
        TriageUpdate(state=VulnState.OPEN.value, reason="Retest")
    assert TriageUpdate(state=VulnState.OPEN.value, reason="  ").reason is None
    assert TriageUpdate(state=CONFIRMED, reason=" Seen [[1]] ").reason == "Seen"
    with pytest.raises(ValidationError):
        TriageUpdate(state=CONFIRMED, note="Seen in prod")


async def test_a_triage_state_is_refused_off_a_finding():
    with pytest.raises(ValidationError):
        NoteCreate(
            target_id=uuid.uuid4(),
            dimension=SurfaceDimension.WEB_ASSETS.value,
            asset_key="api.example.com",
            body="Login page",
            triage_state=CONFIRMED,
        )
    with pytest.raises(ValidationError):
        NoteCreate(
            target_id=uuid.uuid4(),
            dimension=SurfaceDimension.VULNERABILITIES.value,
            asset_key="rce",
            body="Open",
            triage_state=VulnState.OPEN.value,
        )


async def test_no_reason_notes_on_a_plain_state_change(durable_estate, now):
    estate = durable_estate
    sid = await _finding(estate, now)
    await VulnerabilityService(estate.session).triage(
        sid, "rce", TriageUpdate(state=CONFIRMED), estate.user_id
    )
    count = await estate.session.scalar(select(func.count()).select_from(Note))
    assert count == 0


async def test_record_triage_saves_its_reason_as_a_note(
    durable_estate, now, monkeypatch
):
    estate = durable_estate
    await _finding(estate, now)

    async def quiet(*_args, **_kwargs):
        return None

    monkeypatch.setattr(telemetry, "record", quiet)
    monkeypatch.setattr(telemetry, "touch", quiet)
    token = TokenIdentity(
        id=uuid.uuid4(),
        name="agent",
        project_id=estate.project_id,
        capabilities=frozenset({Capability.READ.value, Capability.WRITE.value}),
        issued_by=estate.user_id,
    )
    ctx = ToolContext(session=estate.session, token=token, ui_base_url="")
    args = {"target": "example.com", "fingerprint": "rce"}

    recorded = await server.invoke(
        ctx, "record_triage", {**args, "state": FALSE_POSITIVE, "reason": "Banner only"}
    )
    assert recorded.data["reason"] == "Banner only"
    assert await _reasons(estate) == [("Banner only", FALSE_POSITIVE)]
    explained = await server.invoke(
        ctx, "explain_finding", {"target": "example.com", "finding": "rce"}
    )
    assert explained.data["review"] == {
        "state": FALSE_POSITIVE,
        "reason": "Banner only",
    }

    with pytest.raises(ToolError, match="A reason is saved with"):
        await server.invoke(
            ctx, "record_triage", {**args, "state": VulnState.OPEN.value, "reason": "x"}
        )
    with pytest.raises(InvalidParamsError, match="note"):
        await server.invoke(
            ctx, "record_triage", {**args, "state": CONFIRMED, "note": "Seen in prod"}
        )
