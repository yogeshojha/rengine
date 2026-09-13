from __future__ import annotations

import pytest
import sqlalchemy as sa

from shared.models.http_asset import HttpAsset
from shared.models.subdomain import Subdomain
from shared.services import screenshot_store

pytestmark = pytest.mark.pipeline

_SHOT = "scan/screenshot/a.example.com_443/abc.png"
_DONE = "scan/screenshot/a.example.com_443/abc.webp"
_HASH = 0x0030242430D41010


async def _render(estate, scan: str, name: str, at, *, path: str, phash=None) -> None:
    await estate.hosts(scan, [name], at=at, status=200)
    await estate.session.execute(
        sa.update(Subdomain)
        .where(Subdomain.name == name, Subdomain.scan_id == estate.scans[scan])
        .values(screenshot_path=path, screenshot_phash=phash)
    )
    await estate.session.flush()


async def _pending(estate) -> list:
    return await estate.session.run_sync(
        lambda s: screenshot_store.pending_scans(s, limit=10)
    )


async def test_a_running_scan_is_left_alone(durable_estate, now):
    """A stage still writing would have its path rewritten out from under it."""
    await durable_estate.scan("example.com", "live", at=now, status="running")
    await _render(durable_estate, "live", "a.example.com", now, path=_SHOT)

    assert durable_estate.scans["live"] not in await _pending(durable_estate)


async def test_a_settled_scan_holding_a_png_is_pending(durable_estate, now):
    await durable_estate.scan("example.com", "done", at=now)
    await _render(durable_estate, "done", "b.example.com", now, path=_SHOT, phash=_HASH)

    assert durable_estate.scans["done"] in await _pending(durable_estate)


async def test_a_settled_scan_with_an_unhashed_render_is_pending(durable_estate, now):
    await durable_estate.scan("example.com", "done", at=now)
    await _render(durable_estate, "done", "c.example.com", now, path=_DONE)

    assert durable_estate.scans["done"] in await _pending(durable_estate)


async def test_a_hashed_webp_is_not_pending(durable_estate, now):
    """The beat task has to run out of work or it never stops."""
    await durable_estate.scan("example.com", "done", at=now)
    await _render(durable_estate, "done", "d.example.com", now, path=_DONE, phash=_HASH)

    assert durable_estate.scans["done"] not in await _pending(durable_estate)


async def test_a_rewritten_path_reaches_both_tables(durable_estate, now):
    """The host row and the asset row share a path and have to move together."""
    await durable_estate.scan("example.com", "done", at=now)
    await _render(durable_estate, "done", "e.example.com", now, path=_SHOT)
    await durable_estate.assets("done", ["e.example.com"], at=now)
    await durable_estate.session.execute(
        sa.update(HttpAsset)
        .where(HttpAsset.host == "e.example.com")
        .values(screenshot_path=_SHOT)
    )
    await durable_estate.session.flush()

    await durable_estate.session.run_sync(
        lambda s: screenshot_store._apply(
            s, [{"b_old": _SHOT, "b_phash": _HASH, "b_path": _DONE}]
        )
    )

    for model in (Subdomain, HttpAsset):
        row = (
            await durable_estate.session.execute(
                sa.select(model.screenshot_path, model.screenshot_phash).where(
                    model.screenshot_path.isnot(None)
                )
            )
        ).first()
        assert row.screenshot_path == _DONE, f"{model.__name__} kept the old path"
        assert row.screenshot_phash == _HASH
