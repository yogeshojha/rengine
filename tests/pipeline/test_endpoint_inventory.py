from __future__ import annotations

import pytest
import sqlalchemy as sa

from shared.definitions.endpoints import EndpointSource
from shared.models.endpoint import Endpoint
from shared.services import endpoint_inventory
from shared.services.endpoint_inventory import EndpointObservation
from shared.services.endpoint_noise import NoisePolicy

pytestmark = pytest.mark.pipeline


def _seen(url: str, **kw) -> EndpointObservation:
    return EndpointObservation(url=url, **kw)


async def _upsert(
    estate,
    scan: str,
    observations: list[EndpointObservation],
    source: str = EndpointSource.SEED.value,
):
    sid = estate.scans[scan]
    target_id = await estate._target_of(sid)
    return await estate.session.run_sync(
        lambda s: endpoint_inventory.upsert(
            s,
            scan_id=sid,
            target_id=target_id,
            project_id=estate.project_id,
            source=source,
            observations=observations,
            policy=NoisePolicy.off(),
        )
    )


async def _verify(estate, scan: str, observations: list[EndpointObservation]):
    sid = estate.scans[scan]
    return await estate.session.run_sync(
        lambda s: endpoint_inventory.verify(s, scan_id=sid, observations=observations)
    )


async def _rows(estate, scan: str) -> dict[str, Endpoint]:
    rows = await estate.session.scalars(
        sa.select(Endpoint).where(Endpoint.scan_id == estate.scans[scan])
    )
    return {row.path: row for row in rows}


async def test_a_second_sighting_updates_rather_than_duplicates(estate, now):
    await estate.scan("example.com", "run", at=now)
    urls = [f"https://www.example.com/page/{i}" for i in range(25)]

    first = await _upsert(estate, "run", [_seen(u) for u in urls])
    assert first.created == 25

    again = await _upsert(estate, "run", [_seen(u, title="Second") for u in urls])
    assert again.created == 0
    rows = await _rows(estate, "run")
    assert len(rows) == 25


async def test_verify_applies_probe_results_to_every_row(estate, now):
    await estate.scan("example.com", "run", at=now)
    urls = [f"https://www.example.com/page/{i}" for i in range(30)]
    await _upsert(estate, "run", [_seen(u) for u in urls])

    result = await _verify(
        estate,
        "run",
        [
            _seen(u, is_probed=True, status_code=200 + (i % 3), title=f"T{i}")
            for i, u in enumerate(urls)
        ],
    )

    assert result.updated == 30
    rows = await _rows(estate, "run")
    assert len(rows) == 30
    for i in range(len(urls)):
        row = rows[f"/page/{i}"]
        assert row.is_probed is True
        assert row.status_code == 200 + (i % 3)
        assert row.title == f"T{i}"


async def test_verify_skips_what_was_never_probed(estate, now):
    await estate.scan("example.com", "run", at=now)
    await _upsert(estate, "run", [_seen("https://www.example.com/a")])

    result = await _verify(estate, "run", [_seen("https://www.example.com/a")])

    assert result.updated == 0
    assert (await _rows(estate, "run"))["/a"].is_probed is False


async def test_rows_that_differ_in_shape_are_all_written(estate, now):
    await estate.scan("example.com", "run", at=now)
    await _upsert(
        estate,
        "run",
        [_seen("https://www.example.com/a"), _seen("https://www.example.com/b")],
        source=EndpointSource.SEED.value,
    )

    await _upsert(
        estate,
        "run",
        [
            _seen("https://www.example.com/a", methods=["POST"]),
            _seen("https://www.example.com/b"),
        ],
        source=EndpointSource.CRAWL.value,
    )

    rows = await _rows(estate, "run")
    assert rows["/a"].methods == ["POST"]
    assert EndpointSource.CRAWL.value in rows["/a"].sources
    assert EndpointSource.CRAWL.value in rows["/b"].sources, (
        "the second shape must be written too"
    )
