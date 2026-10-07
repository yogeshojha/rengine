"""Cloud storage buckets: candidates named after a target and the access they allow."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

CLOUD_STORAGE_STAGE = "cloud_storage"

MAX_NAME_LENGTH = 253
MAX_URL_LENGTH = 2000
MAX_WORDS = 50
MAX_WORD_LENGTH = 30
MAX_CANDIDATES = 4000
MAX_ROWS = 1000
PROBE_TIMEOUT = 10
PROBE_WORKERS = 24
LISTING_MAX_BYTES = 200_000
SLOW_DOWN_BACKOFF = 2.0

PROBE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

DEFAULT_WORDS: tuple[str, ...] = (
    "backup",
    "backups",
    "assets",
    "static",
    "media",
    "files",
    "uploads",
    "images",
    "data",
    "public",
    "private",
    "dev",
    "staging",
    "prod",
    "test",
    "logs",
    "db",
    "dump",
    "archive",
    "cdn",
)


class Provider(StrEnum):
    AWS_S3 = "aws_s3"
    GCS = "gcs"
    AZURE_BLOB = "azure_blob"
    FIREBASE_RTDB = "firebase_rtdb"
    DO_SPACES = "do_spaces"
    R2 = "r2"


@dataclass(frozen=True)
class ProviderSpec:
    key: str
    label: str
    guessable: bool


PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec(Provider.AWS_S3.value, "AWS S3", guessable=True),
    ProviderSpec(Provider.GCS.value, "Google Cloud Storage", guessable=True),
    ProviderSpec(Provider.AZURE_BLOB.value, "Azure Blob", guessable=True),
    ProviderSpec(Provider.FIREBASE_RTDB.value, "Firebase", guessable=True),
    ProviderSpec(Provider.DO_SPACES.value, "DigitalOcean Spaces", guessable=True),
    ProviderSpec(Provider.R2.value, "Cloudflare R2", guessable=False),
)

PROVIDER_LABELS: dict[str, str] = {p.key: p.label for p in PROVIDERS}
PROVIDER_ORDER: tuple[str, ...] = tuple(p.key for p in PROVIDERS)
GUESSABLE_PROVIDERS: frozenset[str] = frozenset(p.key for p in PROVIDERS if p.guessable)

DO_REGIONS: tuple[str, ...] = ("nyc3", "sfo3", "ams3", "sgp1", "fra1", "syd1")


class Source(StrEnum):
    REFERENCED = "referenced"
    HOSTNAME = "hostname"
    GUESSED = "guessed"


@dataclass(frozen=True)
class SourceSpec:
    key: str
    label: str
    help: str


SOURCES: tuple[SourceSpec, ...] = (
    SourceSpec(
        Source.REFERENCED.value,
        "Referenced",
        "A CNAME, page or script the scan read points at this bucket.",
    ),
    SourceSpec(
        Source.HOSTNAME.value,
        "Named after a host",
        "A discovered hostname is also the bucket name.",
    ),
    SourceSpec(
        Source.GUESSED.value,
        "Guessed",
        "The bucket name is the target's name joined with a common word.",
    ),
)

SOURCE_LABELS: dict[str, str] = {s.key: s.label for s in SOURCES}
SOURCE_ORDER: tuple[str, ...] = tuple(s.key for s in SOURCES)
SOURCE_RANK: dict[str, int] = {key: i for i, key in enumerate(SOURCE_ORDER)}
# Sources that place a bucket under the target rather than guess at it.
OWNED_SOURCES: frozenset[str] = frozenset(
    {Source.REFERENCED.value, Source.HOSTNAME.value}
)


class Access(StrEnum):
    READABLE = "readable"
    LISTABLE = "listable"
    PROTECTED = "protected"
    MISSING = "missing"


@dataclass(frozen=True)
class AccessSpec:
    key: str
    label: str
    help: str


ACCESS: tuple[AccessSpec, ...] = (
    AccessSpec(
        Access.LISTABLE.value,
        "Listable",
        "Anyone can list the objects in the bucket.",
    ),
    AccessSpec(
        Access.READABLE.value,
        "Readable",
        "Anyone can read the bucket's contents.",
    ),
    AccessSpec(
        Access.PROTECTED.value,
        "Protected",
        "The bucket exists and refuses anonymous access.",
    ),
    AccessSpec(
        Access.MISSING.value,
        "Not found",
        "No bucket answers to this name.",
    ),
)

ACCESS_LABELS: dict[str, str] = {a.key: a.label for a in ACCESS}
ACCESS_ORDER: tuple[str, ...] = tuple(a.key for a in ACCESS)
ACCESS_RANK: dict[str, int] = {key: i for i, key in enumerate(ACCESS_ORDER)}
# An open bucket: its contents are reachable without credentials.
OPEN_ACCESS: frozenset[str] = frozenset({Access.LISTABLE.value, Access.READABLE.value})
# Access values worth a row; a missing name is not stored.
STORED_ACCESS: frozenset[str] = frozenset(
    {Access.LISTABLE.value, Access.READABLE.value, Access.PROTECTED.value}
)


class ReviewState(StrEnum):
    OPEN = "open"
    CONFIRMED = "confirmed"
    IGNORED = "ignored"


STATE_LABELS: dict[str, str] = {
    ReviewState.OPEN.value: "Open",
    ReviewState.CONFIRMED.value: "Confirmed",
    ReviewState.IGNORED.value: "Ignored",
}
