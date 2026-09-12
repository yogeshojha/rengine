from __future__ import annotations

import pytest
import sqlalchemy as sa

from shared.definitions.endpoints import (
    EndpointSource,
    NoiseRule,
    family_for,
    family_shape,
    is_artifact,
    is_ignored_param,
    parse_url,
)
from shared.models.endpoint import Endpoint
from shared.services import endpoint_inventory
from shared.services.endpoint_inventory import EndpointObservation
from shared.services.endpoint_noise import NoisePolicy, Sifter

pytestmark = pytest.mark.pipeline


def _seen(url: str, **kw) -> EndpointObservation:
    return EndpointObservation(url=url, **kw)


async def _upsert(estate, scan, observations, policy=None, sifter=None):
    sid = estate.scans[scan]
    target_id = await estate._target_of(sid)
    return await estate.session.run_sync(
        lambda s: endpoint_inventory.upsert(
            s,
            scan_id=sid,
            target_id=target_id,
            project_id=estate.project_id,
            source=EndpointSource.CRAWL.value,
            observations=observations,
            policy=policy,
            sifter=sifter,
        )
    )


async def _paths(estate, scan: str) -> list[str]:
    rows = await estate.session.scalars(
        sa.select(Endpoint.path).where(Endpoint.scan_id == estate.scans[scan])
    )
    return sorted(rows)


# ---------- pure rules ----------


def test_family_folds_identifiers_language_and_scheme():
    a = parse_url(
        "https://www.example.com/en/vacancies/123/some-long-slug-for-the-post"
    )
    b = parse_url("http://www.example.com/hr-ba/vacancies/9/another-long-slug-for-it")
    assert a is not None
    assert b is not None
    assert a.signature != b.signature
    assert a.family == family_for("www.example.com", 443, a.path, a.params)
    assert family_shape(a.path) == family_shape(b.path) == "/{lang}/vacancies/{id}/{id}"


def test_family_drops_ignored_parameter_names():
    a = family_for("h", 443, "/p", ("id", "ver", "utm_source", "a1b2c3d4e5f6"))
    b = family_for("h", 443, "/p", ("id",))
    assert a == b
    assert family_for("h", 443, "/p", ("id", "q")) != b


def test_ignored_param_names():
    assert is_ignored_param("utm_campaign")
    assert is_ignored_param("itok")
    assert is_ignored_param("1788301181")
    assert is_ignored_param("a1b2c3d4e5f6")
    assert not is_ignored_param("id")
    assert not is_ignored_param("search")
    assert not is_ignored_param("callback")
    assert not is_ignored_param("shipping_address_line_1")
    assert not is_ignored_param("srchtxt")
    assert not is_ignored_param("sku123")


def test_language_segments_are_real_language_tags():
    assert family_shape("/my/account") == "/my/account"
    assert family_shape("/sso/login") == "/sso/login"
    assert family_shape("/id/123") == "/id/{id}"
    assert family_shape("/it/account") == "/{lang}/account"


def test_artifacts():
    assert is_artifact("/api/{{id}}")
    assert is_artifact("/api/${id}")
    assert is_artifact("/x/undefined")
    assert is_artifact('/a"+b+"')
    assert not is_artifact("/about-us")
    assert not is_artifact("/api/v1/users")
    assert not is_artifact("/search/red+blue+green")
    assert not is_artifact("/o'reilly")


# ---------- the gate ----------


async def test_static_artifacts_and_platform_noise_are_not_written(estate, now):
    await estate.scan("example.com", "run", at=now)
    result = await _upsert(
        estate,
        "run",
        [
            _seen("https://www.example.com/logo.png"),
            _seen("https://www.example.com/app.css"),
            _seen("https://www.example.com/fonts/a.woff2"),
            _seen("https://www.example.com/api/{{id}}"),
            _seen("https://www.example.com/feed/"),
            _seen("https://www.example.com/p?replytocom=5"),
            _seen("https://www.example.com/app.js"),
            _seen("https://www.example.com/api/users"),
        ],
    )
    assert result.created == 2
    assert result.dropped == {
        NoiseRule.STATIC.value: 3,
        NoiseRule.ARTIFACT.value: 1,
        NoiseRule.PLATFORM.value: 2,
    }
    assert await _paths(estate, "run") == ["/api/users", "/app.js"]


async def test_tracking_parameters_and_index_files_are_cleaned_not_dropped(estate, now):
    await estate.scan("example.com", "run", at=now)
    result = await _upsert(
        estate,
        "run",
        [
            _seen("https://www.example.com/docs/index.html?utm_source=x&ver=3"),
            _seen("https://www.example.com/docs/"),
            _seen("https://www.example.com/a;jsessionid=ABC/b?id=1&fbclid=9"),
        ],
    )
    assert result.created == 2
    assert result.dropped == {}
    rows = {
        r.path: r
        for r in await estate.session.scalars(
            sa.select(Endpoint).where(Endpoint.scan_id == estate.scans["run"])
        )
    }
    assert set(rows) == {"/docs/", "/a/b"}
    assert rows["/a/b"].params == ["id"]
    assert rows["/a/b"].url == "https://www.example.com/a/b?id=1"


async def test_family_cap_keeps_three_and_counts_the_rest(estate, now):
    await estate.scan("example.com", "run", at=now)
    urls = [
        f"https://www.example.com/vacancies/{i}/slug-number-{i}-of-the-post"
        for i in range(40)
    ]
    result = await _upsert(estate, "run", [_seen(u) for u in urls])
    assert result.created == 3
    assert result.dropped == {NoiseRule.FAMILY.value: 37}

    again = await _upsert(
        estate, "run", [_seen(u) for u in urls[:2]] + [_seen(urls[39])]
    )
    assert again.created == 0
    assert again.updated == 0
    assert again.dropped == {NoiseRule.FAMILY.value: 1}


async def test_family_cap_counts_across_batches_and_sifters(estate, now):
    await estate.scan("example.com", "run", at=now)
    first = [f"https://www.example.com/node/{i}" for i in range(2)]
    second = [f"https://www.example.com/node/{i}" for i in range(2, 6)]
    await _upsert(estate, "run", [_seen(u) for u in first])
    result = await _upsert(estate, "run", [_seen(u) for u in second])
    assert result.created == 1
    assert result.dropped == {NoiseRule.FAMILY.value: 3}


async def test_other_languages_of_a_kept_path_are_dropped(estate, now):
    await estate.scan("example.com", "run", at=now)
    result = await _upsert(
        estate,
        "run",
        [
            _seen("https://www.example.com/en/about"),
            _seen("https://www.example.com/hr-ba/about"),
            _seen("https://www.example.com/bs-latn-ba/about"),
            _seen("https://www.example.com/en/contact"),
            _seen("https://www.example.com/api/v1/users"),
        ],
    )
    assert result.created == 3
    assert result.dropped == {NoiseRule.LOCALE.value: 2}
    assert await _paths(estate, "run") == ["/api/v1/users", "/en/about", "/en/contact"]


async def test_sibling_cap_folds_a_folder_of_slugs(estate, now):
    await estate.scan("example.com", "run", at=now)
    urls = [
        f"https://www.example.com/blog/post-{c}/" for c in "abcdefghijklmnopqrstuvwxyz"
    ]
    result = await _upsert(
        estate, "run", [_seen(u) for u in urls], policy=NoisePolicy(sibling_cap=5)
    )
    assert result.created == 5
    assert result.dropped == {NoiseRule.SIBLINGS.value: 21}


async def test_protected_policy_keeps_parameters_and_never_drops(estate, now):
    await estate.scan("example.com", "run", at=now)
    urls = [f"https://www.example.com/item/{i}?utm_source=x&t=1" for i in range(10)]
    result = await _upsert(
        estate, "run", [_seen(u) for u in urls], policy=NoisePolicy.protected()
    )
    assert result.created == 10
    assert result.dropped == {}
    rows = await estate.session.scalars(
        sa.select(Endpoint).where(Endpoint.scan_id == estate.scans["run"])
    )
    assert {tuple(r.params) for r in rows} == {("t", "utm_source")}


async def test_a_disabled_policy_stores_everything_as_given(estate, now):
    await estate.scan("example.com", "run", at=now)
    result = await _upsert(
        estate,
        "run",
        [
            _seen("https://www.example.com/logo.png?ver=2"),
            _seen("https://www.example.com/feed/"),
        ],
        policy=NoisePolicy.off(),
    )
    assert result.created == 2
    rows = await estate.session.scalars(
        sa.select(Endpoint).where(Endpoint.scan_id == estate.scans["run"])
    )
    assert {r.path: r.params for r in rows} == {"/logo.png": ["ver"], "/feed/": []}


async def test_one_sifter_remembers_across_calls(estate, now):
    await estate.scan("example.com", "run", at=now)
    sid = estate.scans["run"]
    target_id = await estate._target_of(sid)

    def run(session):
        sifter = Sifter(session, sid, NoisePolicy(keep_per_family=2))
        out = []
        for batch in (range(2), range(2, 4)):
            out.append(
                endpoint_inventory.upsert(
                    session,
                    scan_id=sid,
                    target_id=target_id,
                    project_id=estate.project_id,
                    source=EndpointSource.CRAWL.value,
                    observations=[
                        _seen(f"https://www.example.com/page/{i}") for i in batch
                    ],
                    sifter=sifter,
                )
            )
        return out

    first, second = await estate.session.run_sync(run)
    assert first.created == 2
    assert second.created == 0
    assert second.dropped == {NoiseRule.FAMILY.value: 2}


async def test_sibling_cap_counts_folders_already_stored(estate, now):
    await estate.scan("example.com", "run", at=now)
    policy = NoisePolicy(sibling_cap=4)
    first = [f"https://www.example.com/blog/post-{c}/" for c in "abc"]
    second = [f"https://www.example.com/blog/post-{c}/" for c in "defg"]
    await _upsert(estate, "run", [_seen(u) for u in first], policy=policy)
    result = await _upsert(estate, "run", [_seen(u) for u in second], policy=policy)
    assert result.created == 1
    assert result.dropped == {NoiseRule.SIBLINGS.value: 3}
