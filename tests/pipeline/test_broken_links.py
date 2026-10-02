from __future__ import annotations

import pytest

from shared.definitions.broken_links import KIND_SEVERITY, LinkKind
from shared.definitions.vulnerabilities import Severity
from shared.services import broken_links
from shared.services.broken_links import _resources, _worth_checking, is_unregistered

pytestmark = pytest.mark.pipeline

_BODY = """
<html><head>
  <script src="https://analytics.deadvendor.io/a.js"></script>
  <link rel="stylesheet" href="https://cdn.deadvendor.io/s.css">
  <img src="https://img.example.com/logo.png">
  <script src="/local/app.js"></script>
  <iframe src="//widgets.gone-widget.net/w"></iframe>
</head></html>
"""


def test_external_resources_are_read_with_their_tag() -> None:
    found = _resources(_BODY)
    assert found["analytics.deadvendor.io"] == LinkKind.SCRIPT.value
    assert found["cdn.deadvendor.io"] == LinkKind.STYLESHEET.value
    assert found["img.example.com"] == LinkKind.IMAGE.value
    assert found["widgets.gone-widget.net"] == LinkKind.IFRAME.value
    assert all("local" not in host for host in found)


def test_the_strongest_tag_wins_per_host() -> None:
    body = (
        '<img src="https://x.example.com/a.png">'
        '<script src="https://x.example.com/a.js"></script>'
    )
    assert _resources(body)["x.example.com"] == LinkKind.SCRIPT.value


@pytest.mark.parametrize(
    ("tag", "kind"),
    [
        ('<link rel="alternate" href="https://h.example.com/feed">', LinkKind.LINK),
        ('<link rel="canonical" href="https://h.example.com/">', LinkKind.LINK),
        (
            '<link rel=stylesheet href="https://h.example.com/s.css">',
            LinkKind.STYLESHEET,
        ),
        (
            '<link rel="modulepreload" href="https://h.example.com/m.js">',
            LinkKind.SCRIPT,
        ),
        (
            '<link rel="shortcut icon" href="https://h.example.com/f.ico">',
            LinkKind.IMAGE,
        ),
    ],
)
def test_a_link_tag_is_read_by_its_rel(tag: str, kind: LinkKind) -> None:
    assert _resources(tag) == {"h.example.com": kind.value}


def test_severity_matches_the_tag() -> None:
    assert KIND_SEVERITY[LinkKind.SCRIPT.value] == Severity.HIGH.value
    assert KIND_SEVERITY[LinkKind.IFRAME.value] == Severity.HIGH.value
    assert KIND_SEVERITY[LinkKind.IMAGE.value] == Severity.LOW.value


@pytest.mark.parametrize(
    "domain",
    ["intranet.corp", "app.local", "foo.internal", "x.lan", "foo.test", "a.example"],
)
def test_a_domain_under_a_non_public_suffix_is_not_checked(domain: str) -> None:
    assert not _worth_checking(domain, "target.com")


@pytest.mark.parametrize("domain", ["deadvendor.io", "gone-widget.net", "old.dev"])
def test_a_domain_under_a_public_suffix_is_checked(domain: str) -> None:
    assert _worth_checking(domain, "target.com")


def test_quorum_requires_agreement(monkeypatch) -> None:
    # every resolver says NXDOMAIN.
    monkeypatch.setattr(broken_links, "_rcode", lambda _name, _server: 3)
    assert is_unregistered("gone.example", ("a", "b"))

    # one resolver still resolves the domain
    monkeypatch.setattr(
        broken_links, "_rcode", lambda _name, server: 3 if server == "a" else 0
    )
    assert not is_unregistered("live.example", ("a", "b"))


def test_below_quorum_is_not_claimed(monkeypatch) -> None:
    # only one resolver answered.
    monkeypatch.setattr(
        broken_links, "_rcode", lambda _name, server: 3 if server == "a" else None
    )
    assert not is_unregistered("maybe.example", ("a", "b"))
