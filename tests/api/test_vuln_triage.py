from __future__ import annotations

import pytest
from sqlalchemy import select

from app.services.vulnerability import VulnerabilityService
from shared.models.vulnerability import (
    BulkTriageUpdate,
    TriageUpdate,
    VulnerabilityTriage,
)

pytestmark = pytest.mark.api


async def _note(estate) -> str | None:
    return await estate.session.scalar(
        select(VulnerabilityTriage.note).where(VulnerabilityTriage.fingerprint == "rce")
    )


async def test_state_change_keeps_the_stored_note(durable_estate, now):
    estate = durable_estate
    sid = await estate.scan("example.com", "run", at=now)
    await estate.vulns("run", [("rce", "critical")], at=now)
    await estate.session.commit()
    service = VulnerabilityService(estate.session)

    await service.triage(
        sid, "rce", TriageUpdate(state="confirmed", note="Seen in prod"), estate.user_id
    )
    result = await service.triage(
        sid, "rce", TriageUpdate(state="accepted_risk"), estate.user_id
    )
    assert result.note == "Seen in prod"
    assert await _note(estate) == "Seen in prod"

    await service.triage_many(
        sid, BulkTriageUpdate(fingerprints=["rce"], state="confirmed"), estate.user_id
    )
    assert await _note(estate) == "Seen in prod"

    result = await service.triage(
        sid, "rce", TriageUpdate(state="confirmed", note=None), estate.user_id
    )
    assert result.note is None
    assert await _note(estate) is None
