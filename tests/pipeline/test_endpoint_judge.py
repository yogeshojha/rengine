from __future__ import annotations

import pytest
import sqlalchemy as sa

from shared.definitions.endpoints import EndpointSource, NoiseRule
from shared.models.endpoint import Endpoint
from shared.models.http_asset import HttpAsset
from shared.services import endpoint_inventory, endpoint_judge
from shared.services.endpoint_inventory import EndpointObservation
from shared.services.endpoint_judge import Fingerprint
from shared.services.endpoint_noise import NoisePolicy

pytestmark = pytest.mark.pipeline

HOST = "www.example.com"


def _url(path: str) -> str:
    return f"https://{HOST}{path}"


async def _write(
    estate, scan: str, paths: list[str], source=EndpointSource.CRAWL.value
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
            observations=[EndpointObservation(url=_url(p)) for p in paths],
            policy=NoisePolicy.off(),
        )
    )


async def _probe(estate, scan: str, answers: dict[str, dict]):
    sid = estate.scans[scan]
    observations = [
        EndpointObservation(url=_url(path), is_probed=True, **fields)
        for path, fields in answers.items()
    ]
    return await estate.session.run_sync(
        lambda s: endpoint_inventory.verify(s, scan_id=sid, observations=observations)
    )


async def _canary(estate, scan: str, *fingerprints: Fingerprint):
    sid = estate.scans[scan]
    asset = await estate.session.scalar(
        sa.select(HttpAsset).where(HttpAsset.scan_id == sid, HttpAsset.host == HOST)
    )
    await estate.session.run_sync(
        lambda s: endpoint_judge.store_fingerprints(s, {asset.id: list(fingerprints)})
    )


async def _judge(estate, scan: str):
    sid = estate.scans[scan]
    return await estate.session.run_sync(lambda s: endpoint_judge.judge(s, sid))


async def _paths(estate, scan: str) -> set[str]:
    rows = await estate.session.scalars(
        sa.select(Endpoint.path).where(Endpoint.scan_id == estate.scans[scan])
    )
    return set(rows)


def _ok(hash_: str, words: int = 100, lines: int = 10, title: str = "Home") -> dict:
    return {
        "status_code": 200,
        "content_hash": hash_,
        "words": words,
        "lines": lines,
        "title": title,
    }


async def test_soft_404s_match_the_canary_and_are_deleted(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.assets("run", [HOST], at=now)
    await _write(estate, "run", ["/", "/real", "/ghost-1", "/ghost-2", "/ghost-3"])
    await _probe(
        estate,
        "run",
        {
            "/": _ok("root"),
            "/real": _ok("real", words=400, lines=40, title="Real"),
            "/ghost-1": _ok("g1", words=52, lines=8, title="Not here"),
            "/ghost-2": _ok("g2", words=51, lines=8, title="Not here"),
            "/ghost-3": _ok("g3", words=90, lines=8, title="Not here"),
        },
    )
    await _canary(estate, "run", Fingerprint(200, "canary", 50, 8, "Not here"))

    dropped = await _judge(estate, "run")

    assert dropped == {NoiseRule.NOT_FOUND.value: 2}
    assert await _paths(estate, "run") == {"/", "/real", "/ghost-3"}


async def test_404s_and_archive_rot_are_deleted_without_a_canary(estate, now):
    await estate.scan("example.com", "run", at=now)
    await _write(estate, "run", ["/", "/live", "/old"])
    await _write(estate, "run", ["/wayback"], source=EndpointSource.ARCHIVE.value)
    await _probe(
        estate,
        "run",
        {
            "/": _ok("root"),
            "/live": _ok("live"),
            "/old": {"status_code": 404},
            "/wayback": {"status_code": 404},
        },
    )

    dropped = await _judge(estate, "run")

    assert dropped == {NoiseRule.NOT_FOUND.value: 1, NoiseRule.ARCHIVE_ROT.value: 1}
    assert await _paths(estate, "run") == {"/", "/live"}


async def test_identical_bodies_keep_the_shortest_path(estate, now):
    await estate.scan("example.com", "run", at=now)
    paths = ["/", "/a", "/a/b", "/a/b/c", "/other"]
    await _write(estate, "run", paths)
    await _probe(
        estate,
        "run",
        {
            "/": _ok("root"),
            "/a": _ok("same"),
            "/a/b": _ok("same"),
            "/a/b/c": _ok("same"),
            "/other": _ok("other"),
        },
    )

    dropped = await _judge(estate, "run")

    assert dropped == {NoiseRule.SAME_RESPONSE.value: 2}
    assert await _paths(estate, "run") == {"/", "/a", "/other"}


async def test_two_identical_bodies_are_not_enough(estate, now):
    await estate.scan("example.com", "run", at=now)
    await _write(estate, "run", ["/x", "/y"])
    await _probe(estate, "run", {"/x": _ok("same"), "/y": _ok("same")})

    assert await _judge(estate, "run") == {}


async def test_root_body_at_another_path_is_a_catch_all(estate, now):
    await estate.scan("example.com", "run", at=now)
    await _write(estate, "run", ["/", "/anything"])
    await _probe(estate, "run", {"/": _ok("root"), "/anything": _ok("root")})

    dropped = await _judge(estate, "run")

    assert dropped == {NoiseRule.CATCH_ALL.value: 1}
    assert await _paths(estate, "run") == {"/"}


async def test_redirect_fan_in_keeps_one_and_off_scope_goes(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.hosts("run", [HOST], at=now)
    paths = [f"/p/{i}" for i in range(6)] + ["/leave"]
    await _write(estate, "run", paths)
    answers = {
        p: {"status_code": 301, "redirect_location": _url("/login")} for p in paths[:6]
    }
    answers["/leave"] = {
        "status_code": 302,
        "redirect_location": "https://elsewhere.net/",
    }
    await _probe(estate, "run", answers)

    dropped = await _judge(estate, "run")

    assert dropped == {
        NoiseRule.SAME_REDIRECT.value: 5,
        NoiseRule.OFF_SCOPE.value: 1,
    }
    assert await _paths(estate, "run") == {"/p/0"}


async def test_forbidden_pages_are_kept_even_when_identical(estate, now):
    await estate.scan("example.com", "run", at=now)
    paths = ["/admin/", "/backup/", "/private/", "/secret/"]
    await _write(estate, "run", paths)
    await _probe(
        estate,
        "run",
        {p: {"status_code": 403, "content_hash": "denied"} for p in paths},
    )

    assert await _judge(estate, "run") == {}
    assert await _paths(estate, "run") == set(paths)


async def test_similar_bodies_need_ten_and_share_a_title(estate, now):
    await estate.scan("example.com", "run", at=now)
    paths = [f"/post-{i}" for i in range(12)]
    await _write(estate, "run", paths)
    await _probe(
        estate,
        "run",
        {
            p: _ok(f"h{i}", words=500 + i % 3, lines=40, title="Blog")
            for i, p in enumerate(paths)
        },
    )

    dropped = await _judge(estate, "run")

    assert dropped == {NoiseRule.SIMILAR_RESPONSE.value: 11}


async def test_proxy_rows_and_the_root_are_never_deleted(estate, now):
    await estate.scan("example.com", "run", at=now)
    await _write(estate, "run", ["/browsed"], source=EndpointSource.PROXY.value)
    await _write(estate, "run", ["/"])
    await _probe(
        estate,
        "run",
        {"/browsed": {"status_code": 404}, "/": {"status_code": 404}},
    )

    assert await _judge(estate, "run") == {}
    assert await _paths(estate, "run") == {"/", "/browsed"}


async def test_a_rate_limited_or_broken_canary_says_nothing(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.assets("run", [HOST], at=now)
    await _write(estate, "run", ["/a", "/b", "/c"])
    await _probe(
        estate,
        "run",
        {
            "/a": {
                "status_code": 429,
                "content_hash": "wall",
                "title": "Just a moment",
            },
            "/b": {"status_code": 503, "content_hash": "down"},
            "/c": _ok("fine"),
        },
    )
    await _canary(
        estate,
        "run",
        Fingerprint(429, "wall", 20, 5, "Just a moment"),
        Fingerprint(503, "down", 10, 2, None),
    )

    assert await _judge(estate, "run") == {}
    assert await _paths(estate, "run") == {"/a", "/b", "/c"}


async def test_redirects_are_never_judged_by_the_canary(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.assets("run", [HOST], at=now)
    await estate.hosts("run", [HOST], at=now)
    paths = ["/account", "/orders", "/admin/users"]
    await _write(estate, "run", paths)
    gate = {
        "status_code": 302,
        "redirect_location": _url("/login"),
        "content_hash": "e",
    }
    await _probe(estate, "run", dict.fromkeys(paths, gate))
    await _canary(estate, "run", Fingerprint(302, "e", 0, 0, None))

    assert await _judge(estate, "run") == {}
    assert await _paths(estate, "run") == set(paths)
