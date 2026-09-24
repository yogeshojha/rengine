"""Exploitation intelligence: the score feeds, the KEV catalog, and the signals derived from them."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from shared.definitions.ports import ServiceClass


class FeedKind(StrEnum):
    EPSS = "epss"
    KEV = "kev"
    NVD = "nvd"


class FeedStatus(StrEnum):
    EMPTY = "empty"
    READY = "ready"
    STALE = "stale"
    FAILED = "failed"
    SYNCING = "syncing"


FEED_STATUS_LABELS: dict[str, str] = {
    FeedStatus.EMPTY.value: "Not downloaded",
    FeedStatus.READY.value: "Current",
    FeedStatus.STALE.value: "Stale",
    FeedStatus.FAILED.value: "Failed",
    FeedStatus.SYNCING.value: "Downloading",
}


@dataclass(frozen=True)
class FeedSpec:
    kind: str
    label: str
    tagline: str
    description: str
    url: str
    source: str
    source_url: str
    license: str
    rows_table: str
    rows_noun: str


NVD_RELEASE = "https://github.com/fkie-cad/nvd-json-data-feeds/releases/latest/download"

FEEDS: tuple[FeedSpec, ...] = (
    FeedSpec(
        kind=FeedKind.EPSS.value,
        label="EPSS",
        tagline="Exploit probability score",
        description=(
            "Modelled probability that a CVE is exploited in the wild within 30 days. "
            "Recomputed daily."
        ),
        url="https://epss.empiricalsecurity.com/epss_scores-current.csv.gz",
        source="FIRST.org",
        source_url="https://www.first.org/epss/",
        license="Free use with attribution",
        rows_table="epss_scores",
        rows_noun="scored CVEs",
    ),
    FeedSpec(
        kind=FeedKind.KEV.value,
        label="CISA KEV",
        tagline="Known exploited vulnerabilities",
        description=(
            "CVEs with confirmed exploitation in the wild, each with a remediation "
            "deadline."
        ),
        url="https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
        source="CISA",
        source_url="https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
        license="US Government public domain",
        rows_table="kev_entries",
        rows_noun="catalogued CVEs",
    ),
    FeedSpec(
        kind=FeedKind.NVD.value,
        label="NVD",
        tagline="Affected versions per CVE",
        description=(
            "Every published CVE with the software versions it applies to. Matched "
            "against reported versions without sending a request."
        ),
        url=f"{NVD_RELEASE}/CVE-<year>.json.xz",
        source="NIST NVD via fkie-cad",
        source_url="https://github.com/fkie-cad/nvd-json-data-feeds",
        license="US Government public domain",
        rows_table="nvd_cves",
        rows_noun="published CVEs",
    ),
)


FEEDS_BY_KIND: dict[str, FeedSpec] = {spec.kind: spec for spec in FEEDS}


@dataclass(frozen=True)
class ProviderSpec:
    kind: str
    label: str
    tagline: str
    source: str
    source_url: str
    rows_noun: str
    unkeyed_rate: str


VULNX_PROVIDER = ProviderSpec(
    kind="vulnx",
    label="vulnx",
    tagline="Exploit, template and exposure data per CVE",
    source="ProjectDiscovery",
    source_url="https://github.com/projectdiscovery/vulnx",
    rows_noun="cached CVEs",
    unkeyed_rate="10 requests per minute",
)

STALE_AFTER_HOURS = 48


@dataclass(frozen=True)
class ExploitBand:
    key: str
    label: str
    floor: float
    description: str


EXPLOIT_BANDS: tuple[ExploitBand, ...] = (
    ExploitBand("very_likely", "Very likely", 0.5, "EPSS 50% or above."),
    ExploitBand("likely", "Likely", 0.088, "EPSS 8.8% or above."),
    ExploitBand("possible", "Possible", 0.01, "EPSS 1% or above."),
    ExploitBand("unlikely", "Unlikely", 0.0, "EPSS below 1%."),
)

BANDS_BY_KEY: dict[str, ExploitBand] = {band.key: band for band in EXPLOIT_BANDS}
BAND_ORDER: tuple[str, ...] = tuple(band.key for band in EXPLOIT_BANDS)


def exploit_band(score: float | None) -> str | None:
    """The band a score falls in, or None when the CVE has no score."""
    if score is None:
        return None
    for band in EXPLOIT_BANDS:
        if score >= band.floor:
            return band.key
    return EXPLOIT_BANDS[-1].key


class ExploitSignal(StrEnum):
    """The reasons one finding outranks another."""

    KEV = "kev"
    RANSOMWARE = "ransomware"
    OVERDUE = "overdue"
    WEAPONISED = "weaponised"
    FRESH_EXPLOIT = "fresh_exploit"
    LIKELY = "likely"
    REACHABLE = "reachable"
    BYPASSED = "bypassed"
    RANSOM_PATH = "ransom_path"
    UNTESTABLE = "untestable"
    CROWD = "crowd"


TONE_CRITICAL = "critical"
TONE_WARNING = "warning"
TONE_INFO = "info"
TONE_NEUTRAL = "neutral"


@dataclass(frozen=True)
class SignalSpec:
    kind: str
    label: str
    help: str
    weight: int
    tone: str


SIGNALS: tuple[SignalSpec, ...] = (
    SignalSpec(
        ExploitSignal.KEV.value,
        "Known exploited",
        "Listed in CISA KEV.",
        40,
        TONE_CRITICAL,
    ),
    SignalSpec(
        ExploitSignal.RANSOM_PATH.value,
        "Ransomware path",
        "Used in ransomware campaigns. The host exposes a remote access or database service.",
        35,
        TONE_CRITICAL,
    ),
    SignalSpec(
        ExploitSignal.RANSOMWARE.value,
        "Used by ransomware",
        "Listed in CISA ransomware campaigns.",
        25,
        TONE_CRITICAL,
    ),
    SignalSpec(
        ExploitSignal.FRESH_EXPLOIT.value,
        "Exploit published after the scan",
        "A public exploit was published after the scan that recorded this finding.",
        25,
        TONE_CRITICAL,
    ),
    SignalSpec(
        ExploitSignal.OVERDUE.value,
        "Past the CISA deadline",
        "The CISA remediation deadline has passed.",
        20,
        TONE_WARNING,
    ),
    SignalSpec(
        ExploitSignal.WEAPONISED.value,
        "Public exploit available",
        "Working exploit code is published.",
        20,
        TONE_WARNING,
    ),
    SignalSpec(
        ExploitSignal.LIKELY.value,
        "Likely to be exploited",
        "EPSS 8.8% or above.",
        15,
        TONE_WARNING,
    ),
    SignalSpec(
        ExploitSignal.REACHABLE.value,
        "Directly reachable",
        "Answers from the internet. No CDN or WAF.",
        15,
        TONE_WARNING,
    ),
    SignalSpec(
        ExploitSignal.BYPASSED.value,
        "Matched through a WAF",
        "The check matched through a WAF or CDN.",
        15,
        TONE_WARNING,
    ),
    SignalSpec(
        ExploitSignal.CROWD.value,
        "Widely deployed software",
        "Run by more than 100,000 hosts on the internet.",
        5,
        TONE_INFO,
    ),
    SignalSpec(
        ExploitSignal.UNTESTABLE.value,
        "No scanner template",
        "No scanner template covers this CVE.",
        0,
        TONE_INFO,
    ),
)

SIGNALS_BY_KIND: dict[str, SignalSpec] = {spec.kind: spec for spec in SIGNALS}
SIGNAL_ORDER: tuple[str, ...] = tuple(spec.kind for spec in SIGNALS)

MAX_EXPLOIT_SCORE = 100

CROWD_HOSTS = 100_000
RANSOM_SERVICE_CLASSES: frozenset[str] = frozenset(
    {ServiceClass.REMOTE.value, ServiceClass.DATABASE.value}
)


def exploit_score(signals: list[str] | tuple[str, ...]) -> int:
    """A finding's rank is the sum of its signal weights, capped."""
    total = sum(SIGNALS_BY_KIND[s].weight for s in signals if s in SIGNALS_BY_KIND)
    return min(total, MAX_EXPLOIT_SCORE)
