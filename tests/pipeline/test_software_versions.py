from __future__ import annotations

import pytest

from shared.definitions.software import (
    PRODUCTS_BY_KEY,
    Caveat,
    Confidence,
    confidence_of,
)
from shared.services.nvd_corpus import _bounds
from shared.services.software_match import _is_coarse
from shared.utils.software import (
    cpe23,
    normalize_product,
    parse_banner,
    parse_tech,
    version_key,
    version_kind,
)

pytestmark = pytest.mark.pipeline


@pytest.mark.parametrize(
    ("lower", "higher"),
    [
        ("1.9", "1.10"),
        ("1.0", "1.0.1"),
        ("2.4.7", "2.4.52"),
        ("1.18.0", "1.20.0"),
        ("1.0.2k", "1.0.3"),
        ("1.0.2", "1.0.2k"),
        ("1.0.2k", "1.0.2m"),
    ],
)
def test_version_key_orders_releases(lower: str, higher: str) -> None:
    assert version_key(lower) < version_key(higher)


def test_trailing_zeros_do_not_split_a_release() -> None:
    assert version_key("4.0") == version_key("4.0.0")
    assert version_key("7.0") == version_key("7.0.0.0")


def test_version_kind_separates_the_two_schemes() -> None:
    assert version_kind(version_key("1.2.3")) == "n"
    assert version_kind(version_key("a30")) == "a"
    assert version_kind(version_key("1.0.2k")) == "n"


def test_banner_states_product_version_and_distribution() -> None:
    assert parse_banner("nginx/1.18.0 (Ubuntu)") == ("nginx", "1.18.0", "ubuntu")
    assert parse_banner("Microsoft-IIS/10.0") == ("Microsoft-IIS", "10.0", None)
    assert parse_banner("cloudflare") == ("cloudflare", None, None)
    assert parse_banner(None) == (None, None, None)


def test_tech_entry_keeps_only_a_real_version() -> None:
    assert parse_tech("Nginx:1.24.0") == ("Nginx", "1.24.0")
    assert parse_tech("jQuery Migrate:3.4.1") == ("jQuery Migrate", "3.4.1")
    assert parse_tech("cPanel") == ("cPanel", None)
    assert parse_tech("Next.js") == ("Next.js", None)


def test_product_names_normalise_the_way_nvd_writes_them() -> None:
    assert normalize_product("Apache HTTP Server") == "apache_http_server"
    assert normalize_product("Microsoft ASP.NET") == "microsoft_asp.net"
    assert normalize_product("Next.js") == "next.js"


def test_every_alias_names_a_product_and_is_unique() -> None:
    assert len(PRODUCTS_BY_KEY) == len(
        {(p.vendor, p.product, p.key) for p in PRODUCTS_BY_KEY.values()}
    )
    for key, spec in PRODUCTS_BY_KEY.items():
        assert key == normalize_product(key)
        assert spec.product


def test_known_traps_resolve_to_the_right_pair() -> None:
    assert PRODUCTS_BY_KEY["apache_http_server"].product == "http_server"
    assert PRODUCTS_BY_KEY["iis"].product == "internet_information_services"
    assert PRODUCTS_BY_KEY["elementor"].product == "website_builder"
    assert "popper" not in PRODUCTS_BY_KEY


def test_cpe_is_escaped_the_way_the_dictionary_escapes_it() -> None:
    assert cpe23("f5", "nginx", "1.24.0").startswith("cpe:2.3:a:f5:nginx:1.24.0:")
    assert "joomla\\!" in cpe23("joomla", "joomla!", "5.0")


def _match(criteria: str, **bounds: str) -> dict:
    return {"criteria": criteria, "vulnerable": True, **bounds}


def test_a_criteria_without_a_version_is_not_a_match() -> None:
    assert _bounds(_match("cpe:2.3:a:apache:tomcat:*:*:*:*:*:*:*:*")) is None


def test_a_pinned_version_becomes_an_exact_key() -> None:
    parsed = _bounds(_match("cpe:2.3:a:apache:tomcat:9.0.1:*:*:*:*:*:*:*"))
    assert parsed is not None
    assert parsed[2] == version_key("9.0.1")


def test_a_range_keeps_its_bounds_and_inclusivity() -> None:
    parsed = _bounds(
        _match(
            "cpe:2.3:a:f5:nginx:*:*:*:*:*:*:*:*",
            versionStartIncluding="1.0.0",
            versionEndExcluding="1.20.1",
        )
    )
    assert parsed is not None
    kind, start, exact, start_incl, end, end_incl = parsed
    assert kind == "n"
    assert exact is None
    assert start == version_key("1.0.0")
    assert start_incl is True
    assert end == version_key("1.20.1")
    assert end_incl is False


def test_bounds_of_two_schemes_are_refused() -> None:
    assert (
        _bounds(
            _match(
                "cpe:2.3:a:x:y:*:*:*:*:*:*:*:*",
                versionStartIncluding="1.0",
                versionEndExcluding="a30",
            )
        )
        is None
    )


def test_hardware_parts_are_not_software() -> None:
    assert _bounds(_match("cpe:2.3:h:siemens:box:1.0:*:*:*:*:*:*:*")) is None


@pytest.mark.parametrize(
    ("version", "coarse"),
    [("7", True), ("7.58", False), ("1.0.2k", False), ("10", True)],
)
def test_a_bare_major_version_is_a_coarse_match(version: str, coarse: bool) -> None:
    assert _is_coarse(version) is coarse


def test_confidence_counts_what_is_unverified() -> None:
    assert confidence_of([]) == Confidence.HIGH.value
    assert confidence_of([Caveat.BACKPORT.value]) == Confidence.MEDIUM.value
    assert (
        confidence_of([Caveat.BACKPORT.value, Caveat.CONDITIONAL.value])
        == Confidence.LOW.value
    )
    assert confidence_of([Caveat.BACKPORT.value, Caveat.BACKPORT.value]) == (
        Confidence.MEDIUM.value
    )
    assert (
        confidence_of([Caveat.FINGERPRINT.value, Caveat.COARSE.value])
        == Confidence.LOW.value
    )
