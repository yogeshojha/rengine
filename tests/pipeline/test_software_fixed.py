from __future__ import annotations

import uuid

import pytest

from shared.services.software_match import _Component, fixed_releases
from shared.utils.software import version_key, version_kind

pytestmark = pytest.mark.pipeline


def _c(product: str, version: str, coarse: bool = False) -> _Component:
    key = version_key(version) or ""
    return _Component(
        ref=uuid.uuid4(),
        host=None,
        ip=None,
        port=None,
        url=None,
        http_asset_id=uuid.uuid4(),
        port_id=None,
        name=product,
        version=version,
        version_key=key,
        version_kind=version_kind(key) or "n",
        vendor=None,
        product=product,
        source="banner",
        distro=None,
        coarse=coarse,
    )


def test_the_nearest_newer_release_without_the_cve_is_named():
    components = [
        _c("http_server", "2.4.6"),
        _c("http_server", "2.4.41"),
        _c("http_server", "2.4.52"),
        _c("http_server", "2.4.52"),
        _c("http_server", "2.4.65"),
    ]
    carried = {
        ("http_server", "2.4.6"): {"CVE-A", "CVE-B"},
        ("http_server", "2.4.41"): {"CVE-A", "CVE-B"},
        ("http_server", "2.4.52"): {"CVE-B"},
    }
    fixed = fixed_releases(components, carried)

    assert fixed[("http_server", "2.4.6", "CVE-A")] == ("2.4.52", 2)
    assert fixed[("http_server", "2.4.6", "CVE-B")] == ("2.4.65", 1)
    assert fixed[("http_server", "2.4.52", "CVE-B")] == ("2.4.65", 1)


def test_nothing_is_named_when_every_newer_release_carries_it():
    components = [_c("nginx", "1.18.0"), _c("nginx", "1.20.1")]
    carried = {("nginx", "1.18.0"): {"CVE-A"}, ("nginx", "1.20.1"): {"CVE-A"}}
    assert fixed_releases(components, carried) == {}


def test_a_misread_version_is_never_the_fix():
    components = [
        _c("bootstrap", "3.3.7"),
        _c("bootstrap", "4.1.3"),
        _c("bootstrap", "26.0503000"),
    ]
    carried = {
        ("bootstrap", "3.3.7"): {"CVE-A"},
        ("bootstrap", "4.1.3"): {"CVE-A"},
    }
    assert fixed_releases(components, carried) == {}


def test_a_coarse_version_is_neither_judged_nor_named():
    components = [_c("drupal", "7", coarse=True), _c("drupal", "7.98")]
    carried = {("drupal", "7"): {"CVE-A"}}
    assert fixed_releases(components, carried) == {}
