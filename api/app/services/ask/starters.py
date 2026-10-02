"""The questions a finding or a web asset offers before anyone types."""

from __future__ import annotations

from app.services.ask.asset_context import AssetBundle, admin_named, login_page
from shared.definitions.ask import MAX_STARTERS, Verdict
from shared.definitions.vulnerabilities import TEMPLATE_SETS, VulnState
from shared.models.software import SoftwareCve
from shared.models.vulnerability import VulnerabilityRead

EXPOSURE_TAGS = frozenset(
    tag for spec in TEMPLATE_SETS if spec.key == "exposure" for tag in spec.tags
)

ASSET_GENERAL = (
    "What is this web asset?",
    "What should I test by hand first?",
    "What changed since the last scan?",
)


def _first(asks: list[str]) -> list[str]:
    return list(dict.fromkeys(asks))[:MAX_STARTERS]


def for_finding(
    v: VulnerabilityRead, *, verdict: str, software: SoftwareCve | None
) -> list[str]:
    disputed = v.state == VulnState.FALSE_POSITIVE.value
    if disputed:
        asks = ["Is it really a false positive?"]
    elif v.cve_ids:
        asks = [f"Does {v.cve_ids[0]} apply here?"]
    elif {t.lower() for t in v.tags} & EXPOSURE_TAGS:
        asks = ["What does it expose?"]
    else:
        asks = ["Is this exploitable?"]
    asks.append("How do I verify it?")
    if verdict == Verdict.UNCERTAIN.value:
        asks.append("Why is the verdict uncertain?")
    elif v.host_count > 1:
        asks.append("Where else does it fire?")
    elif not disputed:
        fixed = software is not None and software.fixed_in
        asks.append("Which release fixes it?" if fixed else "How do I fix it?")
    return _first(asks)


def for_asset(bundle: AssetBundle) -> list[str]:
    asks: list[str] = []
    if bundle.sub.ai_services:
        asks.append("What does the AI service expose?")
    if admin_named(bundle):
        asks.append("Is this an admin interface?")
    elif login_page(bundle):
        asks.append("What is this login for?")
    if bundle.findings:
        asks.append("Which finding matters most?")
    return _first([*asks, *ASSET_GENERAL])
