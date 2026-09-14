from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from shared.definitions.scan_surface import (
    ClusterSignal,
    is_universal,
    normalize_tech,
    product_tags,
    tags_for_tech,
)
from shared.services.scan_surface import (
    RootCandidate,
    base_rank,
    batch_size,
    batches,
    cluster_rank,
    cluster_roots,
    host_tags,
    parse_root,
    root_value,
    same_origin,
    service_value,
    split,
    tech_groups,
)
from shared.services.vuln_templates import parse_template

pytestmark = pytest.mark.pipeline

BODY = "a" * 64
CERT = "c" * 64


def _root(host: str, **over) -> RootCandidate:
    fields = {
        "asset_id": uuid.uuid4(),
        "value": f"https://{host}",
        "scheme": "https",
        "host": host,
        "port": 443,
        "status": 200,
        "title": "BIPAD",
        "content_hash": BODY,
        "content_length": 4000,
        "ip": "202.45.146.3",
        "a_records": ["202.45.146.3"],
        "tls_fingerprint": CERT,
    }
    fields.update(over)
    return RootCandidate(**fields)


# ---------- normalisation ----------


def test_a_root_is_one_spelling():
    assert root_value("https", "A.Example.com", 443) == "https://a.example.com"
    assert root_value("http", "a.example.com", 80) == "http://a.example.com"
    assert root_value("https", "a.example.com", 8443) == "https://a.example.com:8443"
    assert root_value("https", "2001:db8::1", 443) == "https://[2001:db8::1]"


def test_parse_root_strips_path_query_and_default_port():
    root = parse_root("HTTPS://A.example.com:443/app/index.php?x=1")
    assert root is not None
    assert root.value == "https://a.example.com"
    assert parse_root("http://a.example.com:8080/").value == "http://a.example.com:8080"
    assert parse_root("") is None


def test_a_service_is_host_and_port():
    assert service_value("A.example.com", 8443) == "a.example.com:8443"
    assert service_value("2001:db8::1", 443) == "[2001:db8::1]:443"


# ---------- origin clusters ----------


def test_same_backend_same_body_same_cert_is_one_origin():
    rep = _root("a.bipadportal.gov.np")
    other = _root("b.bipadportal.gov.np")

    signals = same_origin(rep, other)

    assert signals is not None
    assert ClusterSignal.ADDRESS.value in signals
    assert ClusterSignal.CERTIFICATE.value in signals
    assert ClusterSignal.BODY.value in signals


def test_a_different_body_is_a_different_origin():
    assert same_origin(_root("a.x"), _root("b.x", content_hash="b" * 64)) is None


def test_a_different_address_is_a_different_origin():
    other = _root("b.x", ip="10.0.0.2", a_records=["10.0.0.2"])
    assert same_origin(_root("a.x"), other) is None


def test_a_different_status_or_title_is_a_different_origin():
    assert same_origin(_root("a.x"), _root("b.x", status=403)) is None
    assert same_origin(_root("a.x"), _root("b.x", title="Other")) is None


def test_a_short_body_is_not_an_identity():
    rep = _root("a.x", content_hash="e3b0" * 16, content_length=0, words=0, lines=0)
    other = _root("b.x", content_hash="e3b0" * 16, content_length=0, words=0, lines=0)

    signals = same_origin(rep, other)

    assert signals is not None
    assert ClusterSignal.SHAPE.value in signals
    assert ClusterSignal.BODY.value not in signals


def test_a_short_body_with_another_server_header_differs():
    rep = _root("a.x", content_hash="e3b0" * 16, content_length=0, webserver="nginx")
    other = _root("b.x", content_hash="e3b0" * 16, content_length=0, webserver="IIS")
    assert same_origin(rep, other) is None


def test_behind_a_cdn_the_certificate_votes_instead_of_the_address():
    rep = _root("a.x", is_cdn=True, ip="104.16.0.1", a_records=["104.16.0.1"])
    other = _root("b.x", is_cdn=True, ip="104.16.0.9", a_records=["104.16.0.9"])

    signals = same_origin(rep, other)

    assert signals is not None
    assert ClusterSignal.ADDRESS.value not in signals
    assert ClusterSignal.CERTIFICATE.value in signals


def test_behind_a_cdn_without_a_certificate_nothing_is_merged():
    rep = _root("a.x", is_cdn=True, tls_fingerprint=None)
    other = _root("b.x", is_cdn=True, tls_fingerprint=None)
    assert same_origin(rep, other) is None


def test_a_disagreeing_canary_vetoes_and_an_absent_one_abstains():
    canary = [{"status": 404, "hash": "x", "words": 1, "lines": 1, "title": "nf"}]
    rep = _root("a.x", not_found=canary)
    assert same_origin(rep, _root("b.x", not_found=canary)) is not None
    assert ClusterSignal.CANARY.value in same_origin(
        rep, _root("b.x", not_found=canary)
    )
    assert same_origin(rep, _root("b.x", not_found=[{"status": 200}])) is None
    assert ClusterSignal.CANARY.value not in same_origin(rep, _root("b.x"))


def test_the_highest_ranked_member_represents_the_cluster():
    apex = _root("bipadportal.gov.np")
    deep = _root("aathabismun.bipadportal.gov.np")
    for candidate in (apex, deep):
        candidate.rank = base_rank(candidate)

    clusters = cluster_roots([deep, apex])

    assert len(clusters) == 1
    assert clusters[0].representative is apex
    assert clusters[0].members == [deep]
    assert clusters[0].signals[deep.asset_id]


def test_members_are_judged_against_the_representative_only():
    """A has no certificate, B and C carry different ones: B and C never merge."""
    a = _root("a.x", tls_fingerprint=None, rank=30)
    b = _root("b.x", tls_fingerprint="b" * 64, rank=20)
    c = _root("c.x", tls_fingerprint="c" * 64, rank=10)

    clusters = cluster_roots([a, b, c])

    assert [cl.representative.host for cl in clusters] == ["a.x", "c.x"]
    assert [m.host for m in clusters[0].members] == ["b.x"]


def test_ports_and_schemes_never_merge():
    assert same_origin(_root("a.x"), _root("a.x", port=8443)) is None
    assert same_origin(_root("a.x"), _root("a.x", scheme="http", port=80)) is None


# ---------- rank ----------


def test_rank_prefers_answering_uncovered_direct_and_shallow():
    live = _root("a.x")
    dead = _root("b.x", status=500)
    seen = _root("c.x", covered_before=True)
    fronted = _root("d.x", is_cdn=True)
    deep = _root("a.b.c.d.e.x")

    assert base_rank(live) > base_rank(dead)
    assert base_rank(live) > base_rank(seen)
    assert base_rank(live) > base_rank(fronted)
    assert base_rank(live) > base_rank(deep)


def test_a_representative_of_many_outranks_a_loner():
    assert cluster_rank(50.0, 11) > cluster_rank(50.0, 1)
    assert cluster_rank(50.0, 1000) == cluster_rank(50.0, 21)


# ---------- tech to tags ----------

VOCAB = frozenset(
    {
        "nginx",
        "iis",
        "wordpress",
        "wp-plugin",
        "wp-theme",
        "wp",
        "laravel",
        "php",
        "tomcat",
        "geoserver",
    }
)


def test_tech_names_map_to_library_tags():
    tags, unmapped = host_tags(
        tech=["Nginx:1.18.0", "Laravel", "Ubuntu", "Bootstrap", "Zog CMS"],
        cpe=["cpe:2.3:a:apache:tomcat:9.0.1:*:*:*:*:*:*:*"],
        webserver="Microsoft-IIS/10.0",
        software=[{"name": "PHP", "version": "8.1"}],
        vocabulary=VOCAB,
    )
    assert tags == ["iis", "laravel", "nginx", "php", "tomcat"]
    assert unmapped == ["Zog CMS"]


def test_wordpress_opens_the_plugin_and_theme_checks():
    tags, _ = host_tags(
        tech=["WordPress"], cpe=[], webserver=None, software=[], vocabulary=VOCAB
    )
    assert tags == ["wordpress", "wp", "wp-plugin", "wp-theme"]


def test_normalisation_and_aliases():
    assert normalize_tech("Node.js:18") == "nodejs"
    assert normalize_tech("Apache HTTP Server:2.4.6") == "apache http server"
    assert tags_for_tech("Apache HTTP Server") == ("apache",)
    assert tags_for_tech("Ubuntu") == ()
    assert tags_for_tech("Zog CMS") is None


# ---------- template tiers ----------


def _row(
    template_id: str,
    tags: list[str],
    *,
    protocol="http",
    paths=None,
    simple=None,
    requests=1,
):
    return SimpleNamespace(
        template_id=template_id,
        tags=tags,
        protocol=protocol,
        paths=paths if paths is not None else ["{{BaseURL}}/" + template_id],
        simple=bool(simple) if simple is not None else False,
        requests=requests,
    )


def test_generic_and_product_tags():
    assert product_tags(["cve", "cve2021", "geoserver", "ssrf"]) == {"geoserver"}
    assert product_tags(["exposure", "config"]) == frozenset()
    assert product_tags(["exposure", "wordpress"]) == {"wordpress"}
    assert is_universal(["exposure", "config"])
    assert not is_universal(["exposure", "wordpress"])
    assert not is_universal(["cve", "cve2021", "rce"])


def test_split_assigns_every_check_to_one_tier():
    root_only = _row("t-root", ["tech", "detect"], paths=["{{BaseURL}}"], simple=True)
    universal = _row("t-env", ["exposure", "config"])
    product = _row("t-geo", ["cve", "cve2021", "geoserver"])
    blind = _row("t-blind", ["cve", "rce"])
    service = _row("t-ssl", ["ssl"], protocol="ssl")
    name = _row("t-dns", ["dns"], protocol="dns")
    odd = _row("t-whois", ["whois"], protocol="whois")

    plan = split([root_only, universal, product, blind, service, name, odd])

    assert [r.template_id for r in plan.one_request] == ["t-root"]
    assert [r.template_id for r in plan.universal] == ["t-env"]
    assert {r.template_id for r in plan.product} == {"t-geo", "t-blind"}
    assert [r.template_id for r in plan.services] == ["t-ssl"]
    assert [r.template_id for r in plan.names] == ["t-dns"]
    assert [r.template_id for r in plan.unrunnable] == ["t-whois"]
    assert plan.http_count == 4


def test_one_request_is_the_top_paths_of_simple_checks():
    common = [
        _row(f"c{i}", ["tech"], paths=["{{BaseURL}}"], simple=True) for i in range(5)
    ]
    rare = _row("rare", ["tech"], paths=["{{BaseURL}}/rare"], simple=True)
    complex_root = _row("post", ["tech"], paths=["{{BaseURL}}"], simple=False)

    plan = split([*common, rare, complex_root])

    assert len(plan.one_request) == 6
    assert plan.top_paths[0] == "{{BaseURL}}"
    assert complex_root in plan.universal


def test_matched_checks_follow_the_detected_software():
    geo = _row("t-geo", ["cve", "geoserver"])
    wp = _row("t-wp", ["wordpress", "wp-plugin"])
    plan = split([geo, wp])

    assert plan.matched(["geoserver"]) == [geo]
    assert plan.matched(["nginx"]) == []


def test_tech_groups_share_one_invocation_and_fold_the_tail():
    geo = _row("t-geo", ["cve", "geoserver"])
    wp = _row("t-wp", ["wordpress", "wp-plugin"])
    nginx = _row("t-nginx", ["nginx", "misconfig"])
    plan = split([geo, wp, nginx])
    items = [
        SimpleNamespace(tags=["geoserver"]),
        SimpleNamespace(tags=["geoserver"]),
        SimpleNamespace(tags=["wordpress"]),
        SimpleNamespace(tags=["nginx"]),
        SimpleNamespace(tags=[]),
    ]

    groups = tech_groups(items, plan, limit=2)

    assert len(groups) == 2
    assert groups[0].tags == {"geoserver"}
    assert len(groups[0].items) == 2
    assert groups[1].tags == {"wordpress", "nginx"}
    assert {r.template_id for r in groups[1].rows} == {"t-wp", "t-nginx"}


# ---------- batches ----------


def test_batches_are_sized_to_the_rate_and_clamped():
    assert batch_size(cost_per_host=12_000, rate=112, seconds=600) == 5
    assert batch_size(cost_per_host=10, rate=112, seconds=600) == 250
    assert batch_size(cost_per_host=10_000_000, rate=1, seconds=600) == 3
    assert [len(b) for b in batches(range(11), 12_000, 112)] == [5, 5, 1]


# ---------- request shape at parse time ----------

_SIMPLE = """
id: root-detect
info:
  name: Root detect
  severity: info
  tags: tech,detect
http:
  - method: GET
    path:
      - "{{BaseURL}}"
    matchers:
      - type: word
        words: ["x"]
"""

_COMPLEX = """
id: post-thing
info:
  name: Post thing
  severity: high
  tags: cve,cve2021,geoserver
http:
  - raw:
      - |
        POST /geoserver/x HTTP/1.1
        Host: {{Hostname}}
    matchers:
      - type: word
        words: ["x"]
"""

_TWO_PATHS = """
id: env-file
info:
  name: env
  severity: high
  tags: exposure,config
http:
  - method: GET
    path:
      - "{{BaseURL}}/.env"
      - "{{BaseURL}}/app/.env"
    matchers:
      - type: word
        words: ["x"]
"""


def test_parse_template_records_paths_and_simplicity():
    simple = parse_template(_SIMPLE)
    assert simple.paths == ["{{BaseURL}}"]
    assert simple.simple is True

    raw = parse_template(_COMPLEX)
    assert raw.paths == []
    assert raw.simple is False

    two = parse_template(_TWO_PATHS)
    assert two.paths == ["{{BaseURL}}/.env", "{{BaseURL}}/app/.env"]
    assert two.simple is True
