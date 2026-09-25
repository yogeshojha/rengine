"""Lookalike permutations and the verdict each registered one gets."""

from __future__ import annotations

import pytest

from shared.definitions.lookalikes import (
    TECHNIQUE_LABELS,
    VERDICT_ORDER,
    LinkReason,
    Verdict,
)
from shared.services import lookalikes
from shared.services.lookalikes import Lookalike, Page, Records
from stages.lookalike_domains.config import LookalikeDomainsConfig
from stages.lookalike_domains.stage import _registered
from stages.registry import stage_by_name

pytestmark = pytest.mark.pipeline


def _item(**records) -> Lookalike:
    return Lookalike(
        domain="exarnple.com", technique="replacement", records=Records(**records)
    )


def test_permutations_exclude_the_apex_and_carry_a_known_technique():
    names = lookalikes.permutations(
        "example.com", tld_swap=True, words=["login"], cap=10_000
    )
    domains = {d for d, _ in names}
    assert "example.com" not in domains
    assert "example.net" in domains
    assert "example-login.com" in domains
    assert {t for _, t in names} <= set(TECHNIQUE_LABELS)


def test_permutations_rank_homoglyphs_last_under_the_cap():
    names = lookalikes.permutations("example.com", tld_swap=False, words=[], cap=50)
    assert len(names) == 50
    assert all(t != "homoglyph" for _, t in names)


def test_homoglyphs_display_in_unicode():
    assert lookalikes.display("xn--xample-2of.com") != "xn--xample-2of.com"
    assert lookalikes.display("example.com") == "example.com"


def test_a_tld_wildcard_answer_is_not_a_registration():
    wildcard = {"ws": {"64.70.19.203"}}
    parked_by_tld = Lookalike(
        domain="exarnple.ws",
        technique="replacement",
        records=Records(a=["64.70.19.203"]),
    )
    assert not _registered(parked_by_tld, wildcard)
    delegated = Lookalike(
        domain="exarnple.ws",
        technique="replacement",
        records=Records(a=["64.70.19.203"], ns=["ns1.example-dns.net"]),
    )
    assert _registered(delegated, wildcard)


def test_a_redirect_to_the_target_is_held():
    item = _item(a=["192.0.2.1"])
    page = Page(status=200, final_url="https://www.example.com/")
    reason = lookalikes.link_reason(
        apex="example.com",
        records=item.records,
        page=page,
        apex_ns=set(),
        tracked=False,
    )
    assert reason == LinkReason.REDIRECT.value


def test_shared_nameservers_do_not_mark_a_lookalike_held():
    item = _item(ns=["ns1.cloudflare.com"])
    reason = lookalikes.link_reason(
        apex="example.com",
        records=item.records,
        page=None,
        apex_ns={"ns1.cloudflare.com"},
        tracked=False,
    )
    assert reason is None


def test_verdicts_follow_the_ladder():
    copy = _item(a=["192.0.2.1"], mx=["mx.exarnple.com"])
    copy.similarity = 80
    assert lookalikes.verdict(copy) == Verdict.SIMILAR_PAGE.value

    mail = _item(mx=["mx.exarnple.com"])
    assert lookalikes.verdict(mail) == Verdict.MAIL.value

    live = _item(a=["192.0.2.1"])
    live.page = Page(status=200)
    assert lookalikes.verdict(live) == Verdict.LIVE.value

    bare = _item(ns=["ns1.registrar.example"])
    assert lookalikes.verdict(bare) == Verdict.REGISTERED.value
    assert VERDICT_ORDER.index(Verdict.SIMILAR_PAGE.value) == 0


def test_parking_nameservers_and_pages():
    assert lookalikes.parked(Records(ns=["ns1.sedoparking.com"]), None)
    assert not lookalikes.parked(Records(ns=["ns01.domaincontrol.com"]), None)
    page = Page(status=200, title="exarnple.com is for sale", body=b"Buy this domain")
    assert lookalikes.parked(Records(ns=["ns01.domaincontrol.com"]), page)


def test_similar_pages_score_high_and_different_pages_low():
    body = (
        b"<html><title>Example</title>" + b"<p>Sign in to your Example account</p>" * 60
    )
    reference = lookalikes.fuzzy_hash(body)
    assert lookalikes.similarity(reference, body) == 100
    other = b"<html>" + b"<div>completely different content here</div>" * 60
    assert (lookalikes.similarity(reference, other) or 0) < 40


def test_the_stage_is_an_analysis_capability_for_domains():
    spec = stage_by_name()["lookalike_domains"]
    assert spec.group == "analysis"
    assert spec.role == "capability"
    assert "domain" in spec.applies_to


def test_words_are_cleaned():
    cfg = LookalikeDomainsConfig(words=[" Login ", "login", "se cure!", ""])
    assert cfg.words == ["login", "secure"]


def test_a_placeholder_exchange_is_not_mail():
    assert not lookalikes.receives_mail(Records(mx=["localhost"]))
    assert not lookalikes.receives_mail(Records(mx=["", "~"]))
    assert lookalikes.receives_mail(Records(mx=["mx1.privateemail.com"]))


def test_a_marketplace_lander_is_parked():
    page = Page(
        status=200, final_url="https://www.atom.com/name/UBZR", title="Just a moment..."
    )
    assert lookalikes.parked(Records(ns=["ns1.example-dns.net"]), page)


def test_an_error_answer_is_not_a_site():
    item = _item(a=["192.0.2.1"])
    item.page = Page(status=404, final_url="https://exarnple.com/")
    assert lookalikes.verdict(item) == Verdict.REGISTERED.value


def test_titles_are_unescaped():
    assert (
        lookalikes.title_of(b"<title>Uber7 &ndash; Store</title>")
        == "Uber7 \u2013 Store"
    )
