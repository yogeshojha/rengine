from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import pytest
import sqlalchemy as sa

from shared.definitions.endpoints import EndpointSource, keeps_body
from shared.definitions.secrets import (
    FINALIZE_SOURCES,
    STAGE_SOURCES,
    MinerSource,
    SecretSource,
)
from shared.models.endpoint import EndpointResponse
from shared.models.secret import Secret, SecretCoverage, SecretSighting
from shared.models.vulnerability import Vulnerability
from shared.services import endpoint_inventory, retention, secret_mining
from shared.services.endpoint_inventory import EndpointObservation
from shared.services.endpoint_noise import NoisePolicy
from shared.services.secret_mining.corpora import FINDINGS

pytestmark = pytest.mark.pipeline

_KEY_A = "AKIAJ4Q7ZX9M2PLW8KTB"
_KEY_B = "AKIAQ2W8E7R1T9Y3U6I5"
_KEY_C = "AKIAZ9X8C7V6B5N4M3L2"


# ---------- the storage rule ----------


@pytest.mark.parametrize(
    "content_type",
    [
        None,
        "",
        "text/html; charset=utf-8",
        "application/json",
        "text/javascript",
        "application/x-javascript",
        "application/manifest+json",
        "text/plain",
        "application/xml",
        "application/graphql",
    ],
)
def test_a_text_shaped_response_is_stored(content_type):
    assert keeps_body(content_type)


@pytest.mark.parametrize(
    "content_type",
    [
        "image/png",
        "application/pdf",
        "application/octet-stream",
        "font/woff2",
        "video/mp4",
        "application/zip",
    ],
)
def test_a_binary_response_is_not_stored(content_type):
    assert not keeps_body(content_type)


def test_a_finding_without_a_url_reads_its_host_off_matched_at():
    row = SimpleNamespace(
        id=None,
        host=None,
        url=None,
        matched_at="https://api.example.com/v1",
        http_asset_id=None,
        response="HTTP/1.1 200 OK\r\n\r\n",
    )
    [doc] = FINDINGS.documents(row)
    assert doc.host == "api.example.com"
    assert doc.url == "https://api.example.com/v1"
    assert doc.source == SecretSource.FINDING.value


def test_a_finding_without_a_response_is_no_document():
    row = SimpleNamespace(
        id=None,
        host="h",
        url="https://h/",
        matched_at="https://h/",
        http_asset_id=None,
        response=None,
    )
    assert FINDINGS.documents(row) == []


# ---------- the probe stores what it read ----------


async def _upsert(estate, scan: str, urls: list[str]) -> None:
    ids = estate.row_ids(scan)
    await estate.session.run_sync(
        lambda s: endpoint_inventory.upsert(
            s,
            **ids,
            source=EndpointSource.SEED.value,
            observations=[EndpointObservation(url=u) for u in urls],
            policy=NoisePolicy.off(),
        )
    )


async def _verify(estate, scan: str, observations: list[EndpointObservation]):
    sid = estate.scans[scan]
    return await estate.session.run_sync(
        lambda s: endpoint_inventory.verify(s, scan_id=sid, observations=observations)
    )


async def _responses(estate, scan: str) -> dict[str, EndpointResponse]:
    rows = await estate.session.execute(
        sa.text(
            "SELECT e.url, r.response_body, r.raw_response_header "
            "FROM endpoint_responses r JOIN endpoints e ON e.id = r.endpoint_id "
            "WHERE r.scan_id = :sid"
        ),
        {"sid": estate.scans[scan]},
    )
    return {url: (body, header) for url, body, header in rows.all()}


def _probed(
    url: str,
    *,
    content_type: str,
    body: str | None,
    header: str | None = "HTTP/1.1 200 OK\r\nServer: x\r\n",
) -> EndpointObservation:
    return EndpointObservation(
        url=url,
        is_probed=True,
        status_code=200,
        content_type=content_type,
        response_body=body,
        raw_response_header=header,
    )


async def test_a_probed_endpoint_keeps_its_response(durable_estate, now):
    estate = durable_estate
    await estate.scan("example.com", "run", at=now)
    js = "https://www.example.com/app.js"
    png = "https://www.example.com/logo.png"
    await _upsert(estate, "run", [js, png])

    result = await _verify(
        estate,
        "run",
        [
            _probed(js, content_type="application/javascript", body=f'k="{_KEY_A}"'),
            _probed(png, content_type="image/png", body="\x89PNG"),
        ],
    )

    assert result.updated == 2
    assert result.responses_refused == 0
    stored = await _responses(estate, "run")
    assert stored[js][0] == f'k="{_KEY_A}"'
    assert stored[png][0] is None, "a binary body is not stored"
    assert stored[png][1].startswith("HTTP/1.1 200"), "its headers are"


async def test_a_second_probe_replaces_the_stored_response(durable_estate, now):
    estate = durable_estate
    await estate.scan("example.com", "run", at=now)
    url = "https://www.example.com/config.json"
    await _upsert(estate, "run", [url])
    await _verify(
        estate, "run", [_probed(url, content_type="application/json", body="{}")]
    )

    await _verify(
        estate, "run", [_probed(url, content_type="application/json", body='{"v":2}')]
    )

    stored = await _responses(estate, "run")
    assert stored[url][0] == '{"v":2}'
    count = await estate.session.scalar(
        sa.select(sa.func.count())
        .select_from(EndpointResponse)
        .where(EndpointResponse.scan_id == estate.scans["run"])
    )
    assert count == 1


# ---------- the miner reads every corpus ----------


async def _mine(estate, scan: str, *, sources, incremental: bool = False):
    ids = estate.row_ids(scan)
    return await estate.session.run_sync(
        lambda s: secret_mining.mine_scan(
            s,
            **ids,
            sources=sources,
            incremental=incremental,
        )
    )


async def _finding_with_response(
    estate, scan: str, response: str, url: str, now
) -> None:
    await estate.vulns(scan, [("exposed-config", "high")], at=now)
    await estate.session.execute(
        sa.update(Vulnerability)
        .where(Vulnerability.scan_id == estate.scans[scan])
        .values(response=response, url=url)
    )
    await estate.session.flush()


async def _secrets(estate, scan: str) -> dict[str, Secret]:
    rows = await estate.session.scalars(
        sa.select(Secret).where(Secret.scan_id == estate.scans[scan])
    )
    return {row.value: row for row in rows}


async def _coverage(estate, scan: str) -> dict[str, SecretCoverage]:
    rows = await estate.session.scalars(
        sa.select(SecretCoverage).where(SecretCoverage.scan_id == estate.scans[scan])
    )
    return {row.source: row for row in rows}


async def _seed_three_corpora(estate, now) -> None:
    await estate.scan("example.com", "run", at=now)
    await estate.assets(
        "run", ["www.example.com"], at=now, body=f'<script>a="{_KEY_A}"</script>'
    )
    js = "https://www.example.com/app.js"
    await _upsert(estate, "run", [js])
    await _verify(
        estate,
        "run",
        [_probed(js, content_type="text/javascript", body=f'b="{_KEY_B}"')],
    )
    await _finding_with_response(
        estate,
        "run",
        f"HTTP/1.1 200 OK\r\n\r\nc={_KEY_C} a={_KEY_A}",
        "https://www.example.com/.env",
        now,
    )


async def test_the_stage_reads_web_assets_and_endpoints(durable_estate, now):
    estate = durable_estate
    await _seed_three_corpora(estate, now)

    outcome = await _mine(estate, "run", sources=STAGE_SOURCES)

    assert outcome.secrets == 2
    found = await _secrets(estate, "run")
    assert found[_KEY_A].source == SecretSource.BODY.value
    assert found[_KEY_B].source == SecretSource.ENDPOINT_BODY.value
    assert _KEY_C not in found, "findings are read at finalize, not by the stage"
    coverage = await _coverage(estate, "run")
    assert set(coverage) == set(STAGE_SOURCES)
    assert coverage[MinerSource.ENDPOINT_RESPONSES.value].documents_read == 1
    assert coverage[MinerSource.WEB_ASSET_RESPONSES.value].documents_read == 1


async def test_finalize_adds_the_findings_without_losing_the_rest(durable_estate, now):
    estate = durable_estate
    await _seed_three_corpora(estate, now)
    await _mine(estate, "run", sources=STAGE_SOURCES)
    assert await estate.session.run_sync(
        lambda s: secret_mining.stage_mined(s, estate.scans["run"])
    )

    outcome = await _mine(estate, "run", sources=FINALIZE_SOURCES, incremental=True)

    assert outcome.secrets == 1
    found = await _secrets(estate, "run")
    assert set(found) == {_KEY_A, _KEY_B, _KEY_C}
    assert found[_KEY_C].source == SecretSource.FINDING.value
    assert found[_KEY_A].sightings == 2, "the web asset and the finding both carry it"
    sightings = await estate.session.scalars(
        sa.select(SecretSighting.source).where(
            SecretSighting.secret_id == found[_KEY_A].id
        )
    )
    assert sorted(sightings) == [SecretSource.BODY.value, SecretSource.FINDING.value]
    coverage = await _coverage(estate, "run")
    assert set(coverage) == set(MinerSource)


async def test_the_finalize_pass_is_idempotent(durable_estate, now):
    estate = durable_estate
    await _seed_three_corpora(estate, now)
    await _mine(estate, "run", sources=STAGE_SOURCES)
    await _mine(estate, "run", sources=FINALIZE_SOURCES, incremental=True)

    again = await _mine(estate, "run", sources=FINALIZE_SOURCES, incremental=True)

    assert again.secrets == 0
    found = await _secrets(estate, "run")
    assert len(found) == 3
    assert found[_KEY_A].sightings == 2


async def test_a_scan_holding_only_endpoint_responses_is_pending(durable_estate, now):
    estate = durable_estate
    await estate.scan("example.com", "run", at=now)
    js = "https://www.example.com/app.js"
    await _upsert(estate, "run", [js])
    await _verify(
        estate, "run", [_probed(js, content_type="text/javascript", body="x")]
    )

    pending = await estate.session.run_sync(secret_mining.pending_scans)

    assert pending == [estate.scans["run"]]


# ---------- retention ----------


async def test_endpoint_responses_age_out_with_the_bodies(durable_estate, now):
    estate = durable_estate
    old = now - timedelta(days=60)
    await estate.scan("example.com", "aged", at=old)
    js = "https://www.example.com/app.js"
    await _upsert(estate, "aged", [js])
    await _verify(
        estate, "aged", [_probed(js, content_type="text/javascript", body="x")]
    )
    await estate.session.commit()

    result = await estate.session.run_sync(lambda s: retention.prune_evidence(s, 30))

    assert result.bodies_removed == 1
    assert await _responses(estate, "aged") == {}
