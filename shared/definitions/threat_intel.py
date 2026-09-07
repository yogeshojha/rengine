"""Exploitation intelligence: the score feeds, the KEV catalog, and the signals derived from them."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FeedKind(StrEnum):
    EPSS = "epss"
    KEV = "kev"


class FeedStatus(StrEnum):
    EMPTY = "empty"
    READY = "ready"
    STALE = "stale"
    FAILED = "failed"
    SYNCING = "syncing"


FEED_STATUS_LABELS: dict[str, str] = {
    FeedStatus.EMPTY.value: "Not downloaded",
    FeedStatus.READY.value: "Up to date",
    FeedStatus.STALE.value: "Out of date",
    FeedStatus.FAILED.value: "Last refresh failed",
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


FEEDS: tuple[FeedSpec, ...] = (
    FeedSpec(
        kind=FeedKind.EPSS.value,
        label="EPSS",
        tagline="Probability of exploitation",
        description=(
            "For every published CVE, the modelled probability that it will be "
            "exploited in the wild within the next 30 days. Recomputed daily."
        ),
        url="https://epss.empiricalsecurity.com/epss_scores-current.csv.gz",
        source="FIRST.org",
        source_url="https://www.first.org/epss/",
        license="Free to use, no account",
    ),
    FeedSpec(
        kind=FeedKind.KEV.value,
        label="CISA KEV",
        tagline="Confirmed exploited in the wild",
        description=(
            "The Known Exploited Vulnerabilities catalog: CVEs with observed, "
            "confirmed exploitation, each with a remediation deadline."
        ),
        url="https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
        source="CISA",
        source_url="https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
        license="Public domain (US Government)",
    ),
)

FEEDS_BY_KIND: dict[str, FeedSpec] = {spec.kind: spec for spec in FEEDS}

# the feeds republish daily; past this a score is old enough to say so
STALE_AFTER_HOURS = 48


@dataclass(frozen=True)
class ExploitBand:
    key: str
    label: str
    floor: float
    description: str


# 0.088 is the published F1-optimal EPSS threshold; 0.5 matches EPSS_HIGH
EXPLOIT_BANDS: tuple[ExploitBand, ...] = (
    ExploitBand(
        "very_likely", "Very likely", 0.5, "More likely than not to be exploited."
    ),
    ExploitBand("likely", "Likely", 0.088, "Above the threshold most teams act on."),
    ExploitBand("possible", "Possible", 0.01, "Uncommon, but not negligible."),
    ExploitBand("unlikely", "Unlikely", 0.0, "In the long tail of unexploited CVEs."),
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
    """The reasons one finding outranks another. Correlation, not severity."""

    KEV = "kev"
    RANSOMWARE = "ransomware"
    OVERDUE = "overdue"
    WEAPONISED = "weaponised"
    FRESH_EXPLOIT = "fresh_exploit"
    LIKELY = "likely"
    REACHABLE = "reachable"
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


# weights sum well past MAX_EXPLOIT_SCORE; the cap is what keeps the top of the queue flat
SIGNALS: tuple[SignalSpec, ...] = (
    SignalSpec(
        ExploitSignal.KEV.value,
        "Known exploited",
        "CISA lists this CVE as exploited in the wild.",
        40,
        TONE_CRITICAL,
    ),
    SignalSpec(
        ExploitSignal.RANSOM_PATH.value,
        "Ransomware path",
        "Used in ransomware campaigns, and this host also exposes a service ransomware crews reach for.",
        35,
        TONE_CRITICAL,
    ),
    SignalSpec(
        ExploitSignal.RANSOMWARE.value,
        "Used by ransomware",
        "CISA records this CVE in known ransomware campaigns.",
        25,
        TONE_CRITICAL,
    ),
    SignalSpec(
        ExploitSignal.FRESH_EXPLOIT.value,
        "Exploit published since your last scan",
        "A public exploit appeared after the scan that found this. Nothing changed on your side.",
        25,
        TONE_CRITICAL,
    ),
    SignalSpec(
        ExploitSignal.OVERDUE.value,
        "Past the CISA deadline",
        "The federal remediation deadline for this CVE has passed.",
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
        "EPSS puts this above the threshold most teams act on.",
        15,
        TONE_WARNING,
    ),
    SignalSpec(
        ExploitSignal.REACHABLE.value,
        "Directly reachable",
        "The host answers from the internet with no CDN or WAF in front of it.",
        15,
        TONE_WARNING,
    ),
    SignalSpec(
        ExploitSignal.CROWD.value,
        "Mass-scanned software",
        "Hundreds of thousands of hosts run this, so it is swept continuously.",
        5,
        TONE_INFO,
    ),
    SignalSpec(
        ExploitSignal.UNTESTABLE.value,
        "No check exists",
        "No scanner template covers this CVE, so no scan can confirm or clear it.",
        0,
        TONE_INFO,
    ),
)

SIGNALS_BY_KIND: dict[str, SignalSpec] = {spec.kind: spec for spec in SIGNALS}
SIGNAL_ORDER: tuple[str, ...] = tuple(spec.kind for spec in SIGNALS)

MAX_EXPLOIT_SCORE = 100

# an internet population above this is a mass-scanned product
CROWD_HOSTS = 100_000
# services a ransomware crew reaches for once it is inside
RANSOM_SERVICE_CLASSES: frozenset[str] = frozenset({"remote", "database"})


def exploit_score(signals: list[str] | tuple[str, ...]) -> int:
    """A finding's rank is the sum of its signal weights, capped."""
    total = sum(SIGNALS_BY_KIND[s].weight for s in signals if s in SIGNALS_BY_KIND)
    return min(total, MAX_EXPLOIT_SCORE)
