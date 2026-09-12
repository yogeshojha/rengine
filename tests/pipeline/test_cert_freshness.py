from __future__ import annotations

from datetime import timedelta

import pytest
import sqlalchemy as sa

from shared.models.instance_settings import InstanceSettings
from shared.models.subdomain import Subdomain
from shared.services import cert_freshness
from shared.services.cert_freshness import (
    MAX_RUN_SECONDS,
    MIN_RUN_SECONDS,
    Freshness,
    _apply,
    budget,
)

pytestmark = pytest.mark.pipeline


async def _on(estate, value: bool = True) -> None:
    existing = await estate.session.scalar(sa.select(InstanceSettings))
    if existing is None:
        estate.session.add(InstanceSettings(cert_recheck_enabled=value))
    else:
        existing.cert_recheck_enabled = value
    await estate.session.flush()


async def _host(
    estate, scan: str, name: str, *, expires, checked=None, at
) -> Subdomain:
    sid = estate.scans[scan]
    row = Subdomain(
        project_id=estate.project_id,
        scan_id=sid,
        target_id=await estate._target_of(sid),
        name=name,
        sources=["test"],
        discovered_at=at,
        tls_not_after=expires,
        tls_checked_at=checked,
    )
    estate.session.add(row)
    await estate.session.flush()
    return row


async def _due(estate, limit: int = 50) -> list[str]:
    rows = await estate.session.run_sync(lambda s: cert_freshness.due(s, limit=limit))
    return [r.name for r in rows]


async def test_it_never_runs_unasked(estate, now):
    await _on(estate, value=False)
    state = await estate.session.run_sync(cert_freshness.refresh)

    assert state.picked == 0
    assert "re-checking is off" in state.skipped


async def test_it_runs_when_the_instance_asked_for_it(estate, now):
    await _on(estate)
    assert await estate.session.run_sync(cert_freshness.enabled) is True


async def test_a_host_never_checked_is_due(estate, now):
    await _on(estate)
    await estate.scan("example.com", "run", at=now)
    await _host(
        estate, "run", "a.example.com", expires=now + timedelta(days=200), at=now
    )

    assert await _due(estate) == ["a.example.com"]


async def test_a_host_checked_a_moment_ago_is_not(estate, now):
    await _on(estate)
    await estate.scan("example.com", "run", at=now)
    await _host(
        estate,
        "run",
        "a.example.com",
        expires=now + timedelta(days=200),
        checked=now,
        at=now,
    )

    assert await _due(estate) == []


async def test_a_certificate_inside_its_renewal_window_is_asked_sooner(estate, now):
    await _on(estate)
    await estate.scan("example.com", "run", at=now)
    six_hours_ago = now - timedelta(hours=6)
    await _host(
        estate,
        "run",
        "soon.example.com",
        expires=now + timedelta(days=5),
        checked=six_hours_ago,
        at=now,
    )
    await _host(
        estate,
        "run",
        "far.example.com",
        expires=now + timedelta(days=300),
        checked=six_hours_ago,
        at=now,
    )

    assert await _due(estate) == ["soon.example.com"]


async def test_the_nearest_expiry_is_asked_first(estate, now):
    await _on(estate)
    await estate.scan("example.com", "run", at=now)
    for name, days in (("far", 300), ("near", 2), ("mid", 20)):
        await _host(
            estate,
            "run",
            f"{name}.example.com",
            expires=now + timedelta(days=days),
            at=now,
        )

    assert (await _due(estate))[:2] == ["near.example.com", "mid.example.com"]


async def test_a_host_with_no_certificate_is_never_asked(estate, now):
    await _on(estate)
    await estate.scan("example.com", "run", at=now)
    await _host(estate, "run", "plain.example.com", expires=None, at=now)

    assert await _due(estate) == []


async def test_an_excluded_host_is_never_asked(estate, now):
    await _on(estate)
    await estate.scan("example.com", "run", at=now)
    row = await _host(
        estate, "run", "out.example.com", expires=now + timedelta(days=9), at=now
    )
    row.is_excluded = True
    await estate.session.flush()

    assert await _due(estate) == []


async def test_an_older_scans_rows_are_a_record_not_a_claim(estate, now):
    await _on(estate)
    await estate.scan("example.com", "old", at=now - timedelta(days=30))
    await estate.scan("example.com", "new", at=now)
    await _host(estate, "old", "a.example.com", expires=now + timedelta(days=9), at=now)
    await _host(estate, "new", "a.example.com", expires=now + timedelta(days=9), at=now)

    rows = await estate.session.run_sync(lambda s: cert_freshness.due(s, limit=50))
    assert [r.scan_id for r in rows] == [estate.scans["new"]]


def _seen(host: str, *, expires, expired=False, self_signed=False) -> dict:
    return {
        "host": host,
        "not_before": None,
        "not_after": expires,
        "expired": expired,
        "self_signed": self_signed,
        "issuer": "Let's Encrypt",
        "subject_cn": host,
        "fingerprint": "abc",
    }


async def _apply_rows(estate, rows, seen) -> Freshness:
    return await estate.session.run_sync(lambda s: _apply(s, rows, seen))


async def test_a_renewed_certificate_is_written_back_and_counted(estate, now):
    await _on(estate)
    await estate.scan("example.com", "run", at=now)
    row = await _host(
        estate, "run", "a.example.com", expires=now + timedelta(days=3), at=now
    )
    renewed = now + timedelta(days=90)

    state = await _apply_rows(
        estate, [row], {"a.example.com": _seen("a.example.com", expires=renewed)}
    )

    assert (state.changed, state.renewed) == (1, 1)
    await estate.session.refresh(row)
    assert row.tls_not_after == renewed
    assert row.tls_checked_at is not None


async def test_a_certificate_that_did_not_move_is_not_counted_as_change(estate, now):
    await _on(estate)
    await estate.scan("example.com", "run", at=now)
    expires = now + timedelta(days=40)
    row = await _host(estate, "run", "a.example.com", expires=expires, at=now)

    state = await _apply_rows(
        estate, [row], {"a.example.com": _seen("a.example.com", expires=expires)}
    )

    assert (state.changed, state.renewed) == (0, 0)
    await estate.session.refresh(row)
    assert row.tls_checked_at is not None


async def test_a_certificate_replaced_with_a_shorter_one_is_a_change_not_a_renewal(
    estate, now
):
    await _on(estate)
    await estate.scan("example.com", "run", at=now)
    row = await _host(
        estate, "run", "a.example.com", expires=now + timedelta(days=90), at=now
    )

    state = await _apply_rows(
        estate,
        [row],
        {"a.example.com": _seen("a.example.com", expires=now + timedelta(days=2))},
    )

    assert (state.changed, state.renewed) == (1, 0)


async def test_a_host_that_did_not_answer_keeps_what_the_scan_found(estate, now):
    await _on(estate)
    await estate.scan("example.com", "run", at=now)
    expires = now + timedelta(days=9)
    row = await _host(estate, "run", "gone.example.com", expires=expires, at=now)

    state = await _apply_rows(estate, [row], {})

    assert (state.answered, state.changed) == (0, 0)
    await estate.session.refresh(row)
    assert row.tls_not_after == expires, "the scan's observation stands"
    assert row.tls_checked_at is not None, "but it is not asked again in four hours"
    assert await _due(estate) == []


async def test_an_expiry_it_reports_is_stored(estate, now):
    await _on(estate)
    await estate.scan("example.com", "run", at=now)
    row = await _host(
        estate, "run", "a.example.com", expires=now + timedelta(days=1), at=now
    )

    await _apply_rows(
        estate,
        [row],
        {
            "a.example.com": _seen(
                "a.example.com", expires=now - timedelta(days=1), expired=True
            )
        },
    )

    await estate.session.refresh(row)
    assert row.tls_expired is True


def test_a_small_batch_still_gets_a_floor():
    assert budget(1) == MIN_RUN_SECONDS
    assert budget(40) == MIN_RUN_SECONDS


def test_the_budget_grows_with_the_batch():
    assert budget(500) > budget(40)


def test_the_budget_is_capped():
    assert budget(1_000_000) == MAX_RUN_SECONDS
