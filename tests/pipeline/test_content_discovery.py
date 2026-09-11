from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from shared.definitions.endpoints import EndpointSource
from shared.definitions.wordlists import (
    BUILTIN_WORDLISTS,
    DEFAULT_WORDLIST,
    WordlistKind,
)
from shared.enums.scan import StageRole
from stages.content_discovery.config import ContentDiscoveryConfig
from stages.content_discovery.stage import (
    MAX_HIT_SHARE,
    ContentDiscoveryStage,
    _observation,
    _Outcome,
    _Run,
)
from stages.registry import stage_by_name
from tools.ffuf.parser import parse_ffuf_record

pytestmark = pytest.mark.pipeline


def _hit(**over) -> dict:
    return {
        "url": "https://a.example.com/admin",
        "status": 302,
        "length": 358,
        "words": 60,
        "lines": 12,
        "content-type": "text/html; charset=utf-8",
        "redirectlocation": "https://a.example.com/login",
        "host": "a.example.com",
        **over,
    }


def test_a_hit_becomes_an_observation():
    parsed = parse_ffuf_record(_hit())
    assert parsed["url"] == "https://a.example.com/admin"
    assert parsed["status_code"] == 302
    assert parsed["redirect_location"] == "https://a.example.com/login"


def test_the_word_is_read_off_the_url_not_the_input():
    parsed = parse_ffuf_record(_hit(input={"FUZZ": "YWRtaW4="}))
    assert "admin" in parsed["url"]
    assert "YWRtaW4=" not in str(parsed)


@pytest.mark.parametrize(
    "record",
    [
        {},
        {"url": "https://a.example.com/x"},
        {"status": 200},
        {"url": "", "status": 200},
        {"url": "https://a.example.com/x", "status": "200"},
        {"url": "x" * 3000, "status": 200},
    ],
)
def test_anything_that_is_not_a_hit_is_dropped(record: dict):
    assert parse_ffuf_record(record) is None


def test_a_missing_redirect_is_none_not_an_empty_string():
    assert parse_ffuf_record(_hit(redirectlocation=""))["redirect_location"] is None


def test_a_guessed_path_is_stored_as_observed():
    obs = _observation(parse_ffuf_record(_hit()), "Common paths and files")

    assert obs.is_probed is True
    assert obs.status_code == 302
    assert obs.found_on is None, "nothing linked to it; that is the point"
    assert "Common paths and files" in obs.detail


def test_the_detail_says_it_was_guessed():
    obs = _observation(parse_ffuf_record(_hit(status=200)), "My list")
    assert "Guessed from My list" in obs.detail
    assert "answered 200" in obs.detail


def _stage(rows: list[tuple[str, int | None]]) -> ContentDiscoveryStage:
    stage = ContentDiscoveryStage.__new__(ContentDiscoveryStage)
    stage.ctx = SimpleNamespace(scan_id=None)
    stage.session = SimpleNamespace(
        execute=lambda _q: SimpleNamespace(all=lambda: rows)
    )
    return stage


def test_only_sites_that_answered_are_asked():
    picked = _stage([("https://a.example.com", 200), ("https://b.example.com", None)])
    assert picked._hosts(10) == ["https://a.example.com"]


def test_a_site_that_only_errors_is_not_worth_a_thousand_requests():
    assert _stage([("https://a.example.com", 502)])._hosts(10) == []


def test_one_site_is_asked_once():
    rows = [("https://a.example.com/", 200), ("https://a.example.com", 200)]
    assert _stage(rows)._hosts(10) == ["https://a.example.com"]


def test_the_site_budget_is_honoured():
    rows = [(f"https://h{i}.example.com", 200) for i in range(10)]
    assert len(_stage(rows)._hosts(3)) == 3


def test_the_trailing_slash_is_dropped_so_the_url_is_not_doubled():
    assert _stage([("https://a.example.com/", 200)])._hosts(1) == [
        "https://a.example.com"
    ]


def test_it_is_a_capability_a_person_chooses():
    assert ContentDiscoveryStage.role == StageRole.CAPABILITY.value
    assert ContentDiscoveryStage.touches_target is True


def test_it_is_off_until_asked_for():
    assert ContentDiscoveryConfig().enabled is False


def test_it_runs_after_the_probe_and_before_verification():
    plan = stage_by_name()
    assert plan["content_discovery"].level > plan["http_probe"].level
    assert plan["endpoint_probe"].level > plan["content_discovery"].level


def test_it_produces_endpoints_from_live_sites():
    spec = stage_by_name()["content_discovery"]
    assert "endpoints" in spec.produces
    assert "http_assets" in spec.consumes


def test_the_source_has_somewhere_to_come_from():
    assert EndpointSource.FUZZ.value == "fuzz"
    assert (
        ContentDiscoveryConfig().wordlist
        == DEFAULT_WORDLIST[WordlistKind.CONTENT.value]
    )


def test_a_content_wordlist_ships_with_the_image():
    shipped = {w.slug: w for w in BUILTIN_WORDLISTS}
    assert "common-content" in shipped
    assert shipped["common-content"].kind == WordlistKind.CONTENT.value


def test_the_shipped_list_is_ranked_and_real():
    lines = (
        (Path(__file__).resolve().parents[2] / "tools" / "data" / "content.txt")
        .read_text()
        .splitlines()
    )
    assert len(lines) > 1000
    assert "admin" in lines[:200], "the ranking must put what matters near the top"
    assert all("/" not in w for w in lines), "a word is one segment, never a path"


def _outcome(host: str, hits: int, tried: int) -> _Outcome:
    out = _Outcome(host=host)
    out.hits = [
        parse_ffuf_record(_hit(url=f"https://{host}/p{i}")) for i in range(hits)
    ]
    out.settle(tried)
    return out


def test_a_site_that_answers_to_everything_is_not_believed():
    out = _outcome("soft404.example.com", hits=278, tried=300)

    assert out.uncalibrated is True
    assert out.kept == [], "not one of them is stored"


def test_a_site_with_real_content_is_believed():
    out = _outcome("real.example.com", hits=12, tried=300)

    assert out.uncalibrated is False
    assert len(out.kept) == 12


def test_the_threshold_is_a_share_not_a_count():
    assert _outcome("a", hits=30, tried=100).uncalibrated is True
    assert _outcome("a", hits=30, tried=10_000).uncalibrated is False


def test_a_site_at_the_threshold_is_dropped():
    tried = 1000
    assert _outcome("a", hits=int(tried * MAX_HIT_SHARE), tried=tried).uncalibrated


def test_a_site_that_answered_nothing_is_not_flagged():
    assert _outcome("a", hits=0, tried=300).uncalibrated is False


def test_the_run_says_which_sites_it_threw_away():
    run = _Run()
    run.absorb(_outcome("soft404.example.com", hits=290, tried=300))
    run.absorb(_outcome("real.example.com", hits=5, tried=300))

    warning = " ".join(run.warnings(SimpleNamespace(max_minutes=20), 300))
    assert "soft404.example.com" in warning
    assert "Nothing from them was stored" in warning
    assert "real.example.com" not in warning


def test_a_site_that_could_not_be_guessed_against_is_counted_not_swallowed():
    run = _Run()
    failed = _Outcome(host="down.example.com")
    failed.error = "connection refused"
    run.absorb(failed)

    assert run.failed == 1
    assert "could not be guessed against" in " ".join(
        run.warnings(SimpleNamespace(max_minutes=20), 300)
    )


def test_a_budget_that_ran_out_is_reported():
    run = _Run()
    out = _outcome("slow.example.com", hits=2, tried=300)
    out.cut_short = True
    run.absorb(out)

    assert "budget" in " ".join(run.warnings(SimpleNamespace(max_minutes=20), 300))


def test_the_progress_line_names_the_sites_it_dropped():
    run = _Run()
    run.absorb(_outcome("soft404.example.com", hits=290, tried=300))
    assert "answered to everything" in run.note(0, 300, 1)
