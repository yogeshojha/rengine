from __future__ import annotations

import pytest

from shared.utils.tracking import tracking_ids

pytestmark = pytest.mark.pipeline


def test_a_universal_analytics_property_folds_to_its_account():
    body = (
        "ga('create', 'UA-58851320-19', 'auto');"
        "<script>gtag('config','UA-58851320-24')</script>"
    )
    assert tracking_ids(body) == ["UA-58851320"]


def test_every_account_kind_is_read():
    body = """
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-EE5J2VQ9G9"></script>
    <script>gtag('config', 'AW-17044567812');</script>
    (function(w,d,s,l,i){})(window,document,'script','dataLayer','GTM-KT9K7K8');
    data-ad-client="ca-pub-1234567890123456"
    fbq('init', '123456789012345');
    h._hjSettings={hjid:3456789,hjsv:6};
    https://www.clarity.ms/tag/bcu0vs3zxg
    ym(98765432, "init", {});
    <script src="//js.hs-scripts.com/4567890.js"></script>
    """
    assert tracking_ids(body) == [
        "AW-17044567812",
        "G-EE5J2VQ9G9",
        "GTM-KT9K7K8",
        "ca-pub-1234567890123456",
        "clarity:bcu0vs3zxg",
        "fb:123456789012345",
        "hotjar:3456789",
        "hubspot:4567890",
        "ym:98765432",
    ]


def test_an_id_outside_quotes_or_a_url_is_not_read():
    body = "Model G-ABCDEFGH12 and part GTM-ABCDE shipped; UA-1234-5 in prose"
    assert tracking_ids(body) == []


def test_an_empty_page_carries_nothing():
    assert tracking_ids(None) == []
    assert tracking_ids("") == []
