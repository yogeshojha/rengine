"""Exploitation intelligence: the score feeds, the KEV catalog, and the signals derived from them."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


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
    rows_table: str
    rows_noun: str


NVD_RELEASE = "https://github.com/fkie-cad/nvd-json-data-feeds/releases/latest/download"

FEEDS: tuple[FeedSpec, ...] = (
    FeedSpec(
        kind=FeedKind.EPSS.value,
        label="EPSS",
        tagline="Probability of exploitation",
        description=(
            "Modelled probability that a CVE is exploited in the wild within 30 days. "
            "Recomputed daily."
        ),
        url="https://epss.empiricalsecurity.com/epss_scores-current.csv.gz",
        source="FIRST.org",
        source_url="https://www.first.org/epss/",
        license="Free to use, no account",
        rows_table="epss_scores",
        rows_noun="scored CVEs",
    ),
    FeedSpec(
        kind=FeedKind.KEV.value,
        label="CISA KEV",
        tagline="Confirmed exploited in the wild",
        description=(
            "CVEs with confirmed exploitation in the wild, each with a remediation "
            "deadline."
        ),
        url="https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
        source="CISA",
        source_url="https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
        license="Public domain (US Government)",
        rows_table="kev_entries",
        rows_noun="catalogued CVEs",
    ),
    FeedSpec(
        kind=FeedKind.NVD.value,
        label="NVD",
        tagline="Which versions a CVE affects",
        description=(
            "Every published CVE with the software versions it applies to. Matched "
            "against reported versions without sending a request."
        ),
        url=f"{NVD_RELEASE}/CVE-<year>.json.xz",
        source="NIST NVD, mirrored by fkie-cad",
        source_url="https://github.com/fkie-cad/nvd-json-data-feeds",
        license="Public domain (US Government)",
        rows_table="nvd_cves",
        rows_noun="published CVEs",
    ),
)


FEEDS_BY_KIND: dict[str, FeedSpec] = {spec.kind: spec for spec in FEEDS}

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
        "CISA lists this CVE as exploited in the wild.",
        40,
        TONE_CRITICAL,
    ),
    SignalSpec(
        ExploitSignal.RANSOM_PATH.value,
        "Ransomware path",
        "Used in ransomware campaigns, and the host exposes a remote access or database service.",
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
        "Exploit published since the last scan",
        "A public exploit was published after the scan that recorded this finding.",
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
        "EPSS 8.8% or above.",
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
        ExploitSignal.BYPASSED.value,
        "Confirmed through a WAF",
        "A WAF or CDN sits in front of the host and the check succeeded.",
        15,
        TONE_WARNING,
    ),
    SignalSpec(
        ExploitSignal.CROWD.value,
        "Mass-scanned software",
        "Run by more than 100,000 hosts on the internet.",
        5,
        TONE_INFO,
    ),
    SignalSpec(
        ExploitSignal.UNTESTABLE.value,
        "No check exists",
        "No scanner template covers this CVE.",
        0,
        TONE_INFO,
    ),
)

SIGNALS_BY_KIND: dict[str, SignalSpec] = {spec.kind: spec for spec in SIGNALS}
SIGNAL_ORDER: tuple[str, ...] = tuple(spec.kind for spec in SIGNALS)

MAX_EXPLOIT_SCORE = 100

CROWD_HOSTS = 100_000
RANSOM_SERVICE_CLASSES: frozenset[str] = frozenset({"remote", "database"})


def exploit_score(signals: list[str] | tuple[str, ...]) -> int:
    """A finding's rank is the sum of its signal weights, capped."""
    total = sum(SIGNALS_BY_KIND[s].weight for s in signals if s in SIGNALS_BY_KIND)
    return min(total, MAX_EXPLOIT_SCORE)
