"""Ask: the starters a finding or a web asset offers."""

from __future__ import annotations

from collections import Counter

import pytest

from app.services.ask.asset_context import AssetBundle
from app.services.ask.starters import for_asset, for_finding
from app.services.ask.verdict import assess
from shared.definitions.ask import MAX_STARTERS
from shared.definitions.vulnerabilities import VulnState
from shared.models.http_asset import HttpAsset
from shared.models.software import SoftwareCve
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import AssetContext
from tests.api.test_ask import _finding

pytestmark = pytest.mark.api


def _asks(software: SoftwareCve | None = None, **over) -> list[str]:
    v = _finding(**over)
    verdict, _ = assess(v, software=software)
    return for_finding(v, verdict=verdict, software=software)


def _bundle(
    name: str = "shop.example.com",
    *,
    title: str = "Shop",
    ai_services: list[str] | None = None,
    findings: dict[str, int] | None = None,
) -> AssetBundle:
    return AssetBundle(
        sub=Subdomain(name=name, page_title=title, ai_services=ai_services),
        assets=[HttpAsset(title=title)],
        findings=Counter(findings or {}),
        endpoints=0,
        ports=0,
    )


def test_a_cve_check_asks_about_its_own_cve():
    assert _asks() == [
        "Does CVE-2023-7028 apply here?",
        "How do I verify it?",
        "How do I fix it?",
    ]


def test_the_check_kind_shapes_the_first_question():
    assert _asks(cve_ids=[], tags=["config", "git"])[0] == "What does it expose?"
    assert _asks(cve_ids=[], tags=["rce"])[0] == "Is this exploitable?"


def test_the_facts_shape_the_third_question():
    waf = AssetContext.model_construct(waf="Cloudflare", status_code=200)
    assert _asks(asset=waf)[2] == "Why is the verdict uncertain?"
    assert _asks(host_count=4)[2] == "Where else does it fire?"
    fixed = SoftwareCve(product="gitlab", version="16.1.0", fixed_in="16.1.6")
    assert _asks(software=fixed)[2] == "Which release fixes it?"


def test_a_disputed_finding_is_not_asked_for_a_fix():
    assert _asks(state=VulnState.FALSE_POSITIVE.value) == [
        "Is it really a false positive?",
        "How do I verify it?",
    ]


def test_a_web_asset_leads_with_its_own_facts():
    assert for_asset(_bundle(ai_services=["ollama"], findings={"high": 2})) == [
        "What does the AI service expose?",
        "Which finding matters most?",
        "What is this web asset?",
    ]
    assert for_asset(_bundle(title="Sign in"))[0] == "What is this login for?"
    assert for_asset(_bundle("admin.example.com"))[0] == "Is this an admin interface?"


def test_a_plain_web_asset_gets_the_general_questions():
    assert for_asset(_bundle()) == [
        "What is this web asset?",
        "What should I test by hand first?",
        "What changed since the last scan?",
    ]


def test_never_more_than_the_cap_and_never_twice():
    for asks in (
        _asks(host_count=9),
        for_asset(_bundle("admin.example.com", ai_services=["x"], findings={"low": 1})),
    ):
        assert len(asks) <= MAX_STARTERS
        assert len(set(asks)) == len(asks)
