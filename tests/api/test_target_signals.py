from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.services.target_filters import (
    signal_count_columns,
    signal_expr,
    with_whois_join,
)
from shared.models import Target
from shared.models.vulnerability import VulnerabilityTriage

pytestmark = pytest.mark.api

SIGNALS = ("unscanned", "stale", "critical", "high", "medium")


async def _matching(estate, signal: str) -> set:
    rows = await estate.session.execute(
        with_whois_join(select(Target.id)).where(
            Target.project_id == estate.project_id, signal_expr(signal)
        )
    )
    return set(rows.scalars())


async def test_scan_signals_count_the_targets_they_filter(estate, now):
    await estate.scan("fresh.com", "old", at=now - timedelta(days=3))
    await estate.vulns("old", [("rce", "critical"), ("cors", "medium")], at=now)
    await estate.scan("fresh.com", "new", at=now)
    await estate.vulns("new", [("sqli", "high"), ("xss", "critical")], at=now)
    await estate.scan("stale.com", "ancient", at=now - timedelta(days=60))
    await estate.vulns("ancient", [("lfi", "critical")], at=now)
    estate.session.add(
        VulnerabilityTriage(
            project_id=estate.project_id,
            target_id=estate.targets["stale.com"],
            fingerprint="lfi",
            template_id="lfi",
            matched_at="https://www.example.com/",
            state="false_positive",
        )
    )
    await estate.scan("broke.com", "covered", at=now - timedelta(days=2))
    await estate.vulns("covered", [("ssti", "critical")], at=now)
    await estate.scan("broke.com", "empty", at=now)
    await estate.target("idle.com")
    await estate.session.flush()

    assert await _matching(estate, "unscanned") == {estate.targets["idle.com"]}
    assert await _matching(estate, "stale") == {estate.targets["stale.com"]}
    assert await _matching(estate, "critical") == {
        estate.targets["fresh.com"],
        estate.targets["broke.com"],
    }
    assert await _matching(estate, "high") == {estate.targets["fresh.com"]}
    assert await _matching(estate, "medium") == set()

    counts = (
        await estate.session.execute(
            with_whois_join(select(*signal_count_columns()).select_from(Target)).where(
                Target.project_id == estate.project_id
            )
        )
    ).one()
    for signal in SIGNALS:
        assert getattr(counts, signal) == len(await _matching(estate, signal)), signal
