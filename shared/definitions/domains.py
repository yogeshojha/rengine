from __future__ import annotations

import json
from collections.abc import Collection
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from shared.definitions.constants import PURE_CACHE


class RelatedReason(StrEnum):
    PROXY_TRAFFIC = "proxy_traffic"


RELATED_REASON_LABELS: dict[str, str] = {
    RelatedReason.PROXY_TRAFFIC.value: "Reached through a proxy",
}

RELATED_REASON_DETAIL: dict[str, str] = {
    RelatedReason.PROXY_TRAFFIC.value: (
        "A connected proxy reached this domain while testing a target."
    ),
}

PUBLIC_SECOND_LEVEL: frozenset[str] = frozenset(
    {
        "ac.at",
        "co.at",
        "gv.at",
        "or.at",
        "com.ar",
        "edu.ar",
        "gov.ar",
        "net.ar",
        "org.ar",
        "com.au",
        "edu.au",
        "gov.au",
        "id.au",
        "net.au",
        "org.au",
        "com.br",
        "edu.br",
        "gov.br",
        "net.br",
        "org.br",
        "ac.cy",
        "biz.cy",
        "com.cy",
        "ltd.cy",
        "name.cy",
        "net.cy",
        "org.cy",
        "press.cy",
        "pro.cy",
        "tm.cy",
        "ac.cn",
        "com.cn",
        "edu.cn",
        "gov.cn",
        "net.cn",
        "org.cn",
        "com.co",
        "net.co",
        "org.co",
        "com.gr",
        "edu.gr",
        "gov.gr",
        "net.gr",
        "org.gr",
        "com.np",
        "edu.np",
        "gov.np",
        "mil.np",
        "net.np",
        "org.np",
        "ac.ae",
        "co.ae",
        "gov.ae",
        "net.ae",
        "org.ae",
        "com.eg",
        "edu.eg",
        "gov.eg",
        "net.eg",
        "org.eg",
        "com.es",
        "edu.es",
        "gob.es",
        "nom.es",
        "org.es",
        "com.hk",
        "edu.hk",
        "gov.hk",
        "net.hk",
        "org.hk",
        "ac.id",
        "biz.id",
        "co.id",
        "go.id",
        "my.id",
        "net.id",
        "or.id",
        "sch.id",
        "web.id",
        "ac.il",
        "co.il",
        "gov.il",
        "net.il",
        "org.il",
        "ac.in",
        "co.in",
        "edu.in",
        "firm.in",
        "gen.in",
        "gov.in",
        "ind.in",
        "net.in",
        "org.in",
        "res.in",
        "ac.jp",
        "co.jp",
        "go.jp",
        "lg.jp",
        "ne.jp",
        "or.jp",
        "ac.ke",
        "co.ke",
        "go.ke",
        "or.ke",
        "ac.kr",
        "co.kr",
        "go.kr",
        "ne.kr",
        "or.kr",
        "pe.kr",
        "re.kr",
        "com.mx",
        "edu.mx",
        "gob.mx",
        "org.mx",
        "com.my",
        "edu.my",
        "gov.my",
        "net.my",
        "org.my",
        "com.ng",
        "edu.ng",
        "gov.ng",
        "net.ng",
        "org.ng",
        "ac.nz",
        "co.nz",
        "govt.nz",
        "net.nz",
        "org.nz",
        "com.ph",
        "gov.ph",
        "net.ph",
        "org.ph",
        "com.pk",
        "gov.pk",
        "net.pk",
        "org.pk",
        "com.pl",
        "edu.pl",
        "gov.pl",
        "net.pl",
        "org.pl",
        "com.ru",
        "net.ru",
        "org.ru",
        "com.sa",
        "edu.sa",
        "gov.sa",
        "net.sa",
        "org.sa",
        "com.sg",
        "edu.sg",
        "gov.sg",
        "net.sg",
        "org.sg",
        "ac.th",
        "go.th",
        "in.th",
        "or.th",
        "com.tr",
        "edu.tr",
        "gov.tr",
        "net.tr",
        "org.tr",
        "com.tw",
        "edu.tw",
        "gov.tw",
        "net.tw",
        "org.tw",
        "com.ua",
        "gov.ua",
        "net.ua",
        "org.ua",
        "ac.uk",
        "co.uk",
        "gov.uk",
        "me.uk",
        "net.uk",
        "org.uk",
        "sch.uk",
        "com.vn",
        "edu.vn",
        "gov.vn",
        "net.vn",
        "org.vn",
        "ac.za",
        "co.za",
        "gov.za",
        "net.za",
        "org.za",
    }
)

PRIVATE_TLDS: frozenset[str] = frozenset(
    {"local", "localhost", "localdomain", "internal", "intranet", "lan", "home",
     "corp", "default", "svc", "cluster", "test", "example", "invalid"}
)  # fmt: skip

VENDOR_DOMAINS: frozenset[str] = frozenset(
    {
        "akamai.net",
        "akamaiedge.net",
        "akamaihd.net",
        "amazon.com",
        "amazonaws.com",
        "amazonaws-china.com",
        "auth0.com",
        "azureedge.net",
        "azurewebsites.net",
        "cloudfront.net",
        "cloudflare.com",
        "cloudflare.net",
        "edgekey.net",
        "elasticbeanstalk.com",
        "fastly.net",
        "fastlylb.net",
        "firebaseapp.com",
        "ghost.io",
        "github.com",
        "github.io",
        "githubusercontent.com",
        "gitlab.com",
        "gitlab-dedicated.com",
        "googleapis.com",
        "googleusercontent.com",
        "herokuapp.com",
        "herokudns.com",
        "mailgun.org",
        "microsoftonline.com",
        "netlify.app",
        "netlify.com",
        "okta.com",
        "onelogin.com",
        "ooklaserver.net",
        "pantheonsite.io",
        "queue-it.net",
        "myshopify.com",
        "shopify.com",
        "sendgrid.net",
        "trafficmanager.net",
        "windows.net",
        "wpengine.com",
        "zendesk.com",
    }
)


_MIN_LABELS = 2
_SUFFIX_PATH = Path(__file__).parent / "data" / "public_suffixes.json"


THIRD_PARTY_DOMAINS: frozenset[str] = frozenset(
    {
        "adnxs.com",
        "adobedtm.com",
        "adsrvr.org",
        "app.link",
        "bing.com",
        "branch.io",
        "clarity.ms",
        "criteo.com",
        "demdex.net",
        "doubleclick.net",
        "facebook.com",
        "facebook.net",
        "google.com",
        "google-analytics.com",
        "googleadservices.com",
        "googlesyndication.com",
        "googletagmanager.com",
        "gstatic.com",
        "hotjar.com",
        "hs-scripts.com",
        "hubspot.com",
        "instagram.com",
        "intercom.io",
        "licdn.com",
        "linkedin.com",
        "mixpanel.com",
        "newrelic.com",
        "onetrust.com",
        "optimizely.com",
        "pinterest.com",
        "recaptcha.net",
        "segment.com",
        "segment.io",
        "sentry.io",
        "snapchat.com",
        "t.co",
        "taboola.com",
        "tiktok.com",
        "twitter.com",
        "x.com",
        "youtube.com",
        "yandex.ru",
    }
)

IGNORED_DOMAINS: frozenset[str] = frozenset(VENDOR_DOMAINS | THIRD_PARTY_DOMAINS)


@lru_cache(maxsize=1)
def _suffix_data() -> dict[str, list[str]]:
    try:
        return json.loads(_SUFFIX_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


@lru_cache(maxsize=1)
def _suffix_rules() -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    data = _suffix_data()
    return (
        frozenset(data.get("suffixes", ())) | PUBLIC_SECOND_LEVEL,
        frozenset(data.get("wildcards", ())),
        frozenset(data.get("exceptions", ())),
    )


@lru_cache(maxsize=1)
def _public_tlds() -> frozenset[str]:
    return frozenset(_suffix_data().get("tlds", ()))


@lru_cache(maxsize=PURE_CACHE)
def is_public_tld(name: str) -> bool:
    """The last label of `name` is a top-level domain on the ICANN public suffix list."""
    label = name.strip().lower().rstrip(".").rsplit(".", 1)[-1]
    try:
        label = label.encode("idna").decode("ascii")
    except UnicodeError:
        return False
    return label in _public_tlds()


def _suffix_length(labels: list[str]) -> int:
    """Labels in the longest public suffix the name ends with."""
    suffixes, wildcards, exceptions = _suffix_rules()
    for size in range(len(labels), 0, -1):
        candidate = ".".join(labels[-size:])
        if candidate in exceptions:
            return size - 1
        if candidate in suffixes:
            return size
        if size > 1 and ".".join(labels[-(size - 1) :]) in wildcards:
            return size
    return 1


def target_zone(value: str) -> str:
    """The zone a target owns: its registrable domain, or itself when it is a registry."""
    host = value.strip().lower().rstrip(".").removeprefix("*.")
    return registrable_domain(host) or host


def owning_zone(apex: str, zones: Collection[str]) -> str | None:
    """The zone in `zones` that is `apex` or a registry `apex` sits under."""
    labels = [part for part in apex.split(".") if part]
    for start in range(len(labels) - 1):
        candidate = ".".join(labels[start:])
        if candidate in zones:
            return candidate
    return None


@lru_cache(maxsize=PURE_CACHE)
def registrable_domain(hostname: str) -> str:
    """The registrable domain under the ICANN public suffix list; empty for a suffix."""
    host = hostname.strip().lower().rstrip(".").removeprefix("*.")
    labels = [part for part in host.split(".") if part]
    if len(labels) < _MIN_LABELS:
        return ""
    if labels[-1].isdigit():
        return ""
    size = _suffix_length(labels)
    return "" if size >= len(labels) else ".".join(labels[-(size + 1) :])


TAKEOVER_FINGERPRINTS: tuple[tuple[str, str], ...] = (
    ("s3.amazonaws.com", "AWS S3"),
    ("s3-website", "AWS S3"),
    ("cloudfront.net", "AWS CloudFront"),
    ("github.io", "GitHub Pages"),
    ("herokuapp.com", "Heroku"),
    ("herokudns.com", "Heroku"),
    ("herokussl.com", "Heroku"),
    ("azurewebsites.net", "Azure"),
    ("cloudapp.net", "Azure"),
    ("cloudapp.azure.com", "Azure"),
    ("trafficmanager.net", "Azure"),
    ("blob.core.windows.net", "Azure"),
    ("azureedge.net", "Azure"),
    ("myshopify.com", "Shopify"),
    ("fastly.net", "Fastly"),
    ("ghost.io", "Ghost"),
    ("wpengine.com", "WP Engine"),
    ("zendesk.com", "Zendesk"),
    ("surge.sh", "Surge"),
    ("bitbucket.io", "Bitbucket"),
    ("statuspage.io", "Statuspage"),
    ("uservoice.com", "UserVoice"),
    ("netlify.app", "Netlify"),
    ("netlify.com", "Netlify"),
    ("readme.io", "Readme"),
    ("pantheonsite.io", "Pantheon"),
    ("unbouncepages.com", "Unbounce"),
    ("tilda.ws", "Tilda"),
    ("helpscoutdocs.com", "Help Scout"),
    ("launchrock.com", "LaunchRock"),
    ("wordpress.com", "WordPress.com"),
)


@lru_cache(maxsize=PURE_CACHE)
def takeover_provider(cname: str) -> str | None:
    """The takeover provider a CNAME points at, or None."""
    host = cname.strip().lower().rstrip(".")
    for suffix, provider in TAKEOVER_FINGERPRINTS:
        if host == suffix or host.startswith(f"{suffix}.") or f".{suffix}" in host:
            return provider
    return None
