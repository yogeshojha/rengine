"""Ask: what a tool result and the finding context may carry to the provider."""

from __future__ import annotations

import pytest

from app.services.ask import context, tools
from app.services.ask.verdict import assess
from shared.definitions.surface import SurfaceDimension
from shared.services.scan_resolve import MASK

pytestmark = pytest.mark.api

AWS_KEY = "AKIA" + "Q3WK9ZL2MX7VP4NR"
BEARER = "Bearer eyJhbGciOiJIUzI1NiJ9.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def test_scrub_masks_string_leaves_at_any_depth():
    payload = {
        "evidence": {
            "curl": f"curl -H 'Authorization: {BEARER}' https://x/",
            "extracted": [AWS_KEY, "plain"],
        },
        "rows": [{"value": AWS_KEY, "n": 3}],
    }
    out = tools.scrub(payload)
    text = str(out)
    assert AWS_KEY not in text
    assert BEARER not in text
    assert MASK in out["evidence"]["curl"]
    assert out["evidence"]["extracted"][1] == "plain"
    assert out["rows"][0]["n"] == 3


def test_secret_rows_are_refused_before_the_tool_runs():
    assert tools.reads_secrets(
        "query_assets", {"dimension": SurfaceDimension.SECRETS.value}
    )
    assert not tools.reads_secrets(
        "query_assets", {"dimension": SurfaceDimension.WEB_ASSETS.value}
    )
    assert not tools.reads_secrets("group_assets", {"dimension": "secrets"})


def test_secret_values_are_refused_through_groups_and_compare():
    secrets = SurfaceDimension.SECRETS.value
    assert tools.reads_secrets(
        "group_assets", {"dimension": secrets, "group_by": "value"}
    )
    assert tools.reads_secrets("compare_runs", {"dimension": secrets})
    assert not tools.reads_secrets(
        "group_assets", {"dimension": secrets, "group_by": "secret"}
    )
    assert not tools.reads_secrets(
        "group_assets", {"dimension": "web_assets", "group_by": "value"}
    )
    assert not tools.reads_secrets("compare_runs", {"target": "example.com"})


async def test_call_refuses_secrets_without_invoking(monkeypatch):
    async def boom(*args, **kwargs):
        msg = "invoked"
        raise AssertionError(msg)

    monkeypatch.setattr(tools.server, "invoke", boom)
    text, step = await tools.call(
        None, "query_assets", {"dimension": SurfaceDimension.SECRETS.value}
    )
    assert text == tools.SECRETS_REFUSED
    assert step.status == "failed"


def test_context_masks_extracted_values_matched_at_and_reason(finding):
    v = finding(
        extracted_results=[AWS_KEY],
        matched_at=f"https://git.example.com/?token={AWS_KEY}",
        reason=f"key was {AWS_KEY}",
        response=f"HTTP/1.1 200 OK\n\nkey={AWS_KEY}",
    )
    _, facts = assess(v)
    ctx = context.build(v, facts=facts, verdict="Likely real", target="example.com")
    assert AWS_KEY not in ctx.system
    assert ctx.masked >= 1
    assert all(AWS_KEY not in (f.detail or "") for f in facts)


def test_a_credential_check_hides_its_extracted_values(finding):
    v = finding(
        template_id="generic-token-exposure",
        tags=["exposure", "token"],
        extracted_results=["plain-looking-value-9"],
    )
    assert context.hides_extracted(v)
    _, facts = assess(v)
    ctx = context.build(v, facts=facts, verdict="Likely real", target="example.com")
    assert "plain-looking-value-9" not in ctx.system
    assert f'"extracted": ["{MASK}"]' in ctx.system
    assert all("plain-looking" not in (f.detail or "") for f in facts)
    assert not context.hides_extracted(finding(tags=["cve", "gitlab"]))


def test_masked_response_keeps_its_line_count(finding):
    marker = "RSA PRIVATE KEY-----"
    key_block = (
        f"-----BEGIN {marker}\n"
        + "\n".join(["MIIEpAIBAAKCAQEA" + "A" * 48] * 6)
        + f"\n-----END {marker}"
    )
    response = f"HTTP/1.1 200 OK\n\n{key_block}\nafter: 1"
    v = finding(response=response, extracted_results=["after: 1"])
    _, facts = assess(v)
    ctx = context.build(v, facts=facts, verdict="Likely real", target="example.com")
    assert ctx.response_lines == len(response.split("\n"))
    last = response.split("\n").index("after: 1") + 1
    assert f"{last:>4}| after: 1" in ctx.system
    assert any(f.lines == [last] for f in facts)


@pytest.fixture
def finding():
    from tests.api.test_ask import _finding  # noqa: PLC0415

    return _finding
