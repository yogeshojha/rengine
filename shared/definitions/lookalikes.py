"""Lookalike domains: registered permutations of a target's domain."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

LOOKALIKE_STAGE = "lookalike_domains"

MAX_DOMAIN_LENGTH = 253
MAX_TITLE_LENGTH = 300
MAX_URL_LENGTH = 2000
MAX_REGISTRAR_LENGTH = 200
MAX_RECORDS = 20

MAX_PERMUTATIONS = 6000
MAX_FETCHES = 300
MAX_RDAP = 40
FETCH_TIMEOUT = 10
FETCH_MAX_BYTES = 1_000_000
FETCH_WORKERS = 16
MAX_REDIRECTS = 5
SIMILAR_AT = 40
LIVE_BELOW = 400
FETCH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


class Verdict(StrEnum):
    SIMILAR_PAGE = "similar_page"
    MAIL = "mail"
    LIVE = "live"
    PARKED = "parked"
    REGISTERED = "registered"
    LINKED = "linked"


@dataclass(frozen=True)
class VerdictSpec:
    key: str
    label: str
    help: str
    tone: str


VERDICTS: tuple[VerdictSpec, ...] = (
    VerdictSpec(
        Verdict.SIMILAR_PAGE.value,
        "Similar page",
        f"Page similarity to the target's page at or above {SIMILAR_AT}%.",
        "critical",
    ),
    VerdictSpec(
        Verdict.MAIL.value,
        "MX configured",
        "Publishes an MX record.",
        "high",
    ),
    VerdictSpec(
        Verdict.LIVE.value,
        "Web content",
        "Answers HTTP with a 2xx or 3xx status.",
        "medium",
    ),
    VerdictSpec(
        Verdict.PARKED.value,
        "Parked",
        "Parking nameservers, a parking page or a domain marketplace.",
        "low",
    ),
    VerdictSpec(
        Verdict.REGISTERED.value,
        "Registered",
        "Resolves or has nameservers. No 2xx or 3xx HTTP answer.",
        "low",
    ),
    VerdictSpec(
        Verdict.LINKED.value,
        "Linked to target",
        "Redirects to the target, shares its nameservers or is a project target.",
        "none",
    ),
)

VERDICT_ORDER: tuple[str, ...] = tuple(v.key for v in VERDICTS)
VERDICT_RANK: dict[str, int] = {key: i for i, key in enumerate(VERDICT_ORDER)}
THREAT_VERDICTS: frozenset[str] = frozenset(
    {Verdict.SIMILAR_PAGE.value, Verdict.MAIL.value, Verdict.LIVE.value}
)


class LinkReason(StrEnum):
    REDIRECT = "redirect"
    NAMESERVERS = "nameservers"
    TARGET = "target"


LINK_LABELS: dict[str, str] = {
    LinkReason.REDIRECT.value: "Redirects to the target",
    LinkReason.NAMESERVERS.value: "Same nameservers as the target",
    LinkReason.TARGET.value: "Project target",
}


class LookalikeState(StrEnum):
    OPEN = "open"
    REVIEWED = "reviewed"
    IGNORED = "ignored"


STATE_LABELS: dict[str, str] = {
    LookalikeState.OPEN.value: "Open",
    LookalikeState.REVIEWED.value: "Reviewed",
    LookalikeState.IGNORED.value: "Ignored",
}

TLD_SWAP = "tld-swap"
DICTIONARY = "dictionary"

TECHNIQUE_LABELS: dict[str, str] = {
    "addition": "Added letter",
    "bitsquatting": "Bit flip",
    "cyrillic": "Cyrillic",
    "homoglyph": "Homoglyph",
    "hyphenation": "Hyphen",
    "insertion": "Inserted key",
    "omission": "Missing letter",
    "plural": "Plural",
    "repetition": "Repeated letter",
    "replacement": "Adjacent key",
    "subdomain": "Dot inserted",
    "transposition": "Swapped letters",
    "vowel-swap": "Vowel swap",
    "various": "Common typo",
    DICTIONARY: "Added word",
    TLD_SWAP: "Other TLD",
}

SWAP_TLDS: tuple[str, ...] = (
    "com",
    "net",
    "org",
    "co",
    "io",
    "info",
    "biz",
    "app",
    "dev",
    "online",
    "site",
    "xyz",
    "shop",
    "store",
    "cloud",
    "live",
    "us",
    "uk",
    "eu",
    "de",
    "in",
    "me",
    "top",
    "cc",
)

DEFAULT_WORDS: tuple[str, ...] = (
    "login",
    "secure",
    "account",
    "support",
    "portal",
    "verify",
    "auth",
    "sso",
    "mail",
    "online",
)

PARKING_NAMESERVERS: tuple[str, ...] = (
    "above.com",
    "bodis.com",
    "dan.com",
    "dns-parking.com",
    "domaincontrol.com",
    "fabulous.com",
    "parkingcrew.net",
    "parklogic.com",
    "rookdns.com",
    "sedoparking.com",
    "smartname.com",
    "afternic.com",
    "undeveloped.com",
    "hugedomains.com",
    "namebrightdns.com",
    "uniregistrymarket.link",
    "dnsowl.com",
    "namefind.com",
    "cashparking.com",
    "mxmpark.com",
    "squadhelp.com",
    "atom.com",
    "namestar.com",
    "brandbucket.com",
    "dyna-ns.net",
    "parkingspa.com",
    "voodoo.com",
    "ztomy.com",
)

SALE_HOSTS: frozenset[str] = frozenset(
    {
        "afternic.com",
        "atom.com",
        "brandbucket.com",
        "buydomains.com",
        "dan.com",
        "ddot.in",
        "domainmarket.com",
        "godaddy.com",
        "gritbrokerage.com",
        "hugedomains.com",
        "namestar.com",
        "paipinc.com",
        "sedo.com",
        "squadhelp.com",
        "startupnames.com",
        "telepathy.com",
        "undeveloped.com",
    }
)

# registrar default DNS: parked only with a parking page
PARKING_NS_NEEDS_PAGE: frozenset[str] = frozenset({"domaincontrol.com", "dnsowl.com"})

PARKING_PHRASES: tuple[str, ...] = (
    "domain is for sale",
    "domain may be for sale",
    "buy this domain",
    "this domain is parked",
    "parked free",
    "parkingcrew",
    "sedoparking",
    "domain for sale",
    "make an offer",
    "hugedomains",
    "is available for purchase",
    "related searches",
    "coming soon",
    "domain names",
    "this website is for sale",
)

NO_MAIL: frozenset[str] = frozenset({"", "localhost", "~", "."})
