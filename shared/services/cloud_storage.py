"""Cloud storage buckets: build candidate names, probe each provider, write rows."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from http import HTTPStatus
from urllib.parse import urlsplit

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from shared.definitions.cloud_storage import (
    DO_REGIONS,
    GUESSABLE_PROVIDERS,
    LISTING_MAX_BYTES,
    MAX_CANDIDATES,
    MAX_NAME_LENGTH,
    MAX_URL_LENGTH,
    OWNED_SOURCES,
    PROBE_USER_AGENT,
    STORED_ACCESS,
    Access,
    Provider,
    Source,
)
from shared.models.cloud_storage import CloudBucket
from shared.utils.datetime import utc_now
from shared.utils.text import strip_nul

_LABEL = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
_CONTENTS = re.compile(rb"<Contents>")


class ThrottledError(Exception):
    """A provider asked the scan to slow down."""


@dataclass(frozen=True)
class Candidate:
    name: str
    source: str
    provider: str | None = None


@dataclass
class Probe:
    access: str
    url: str
    region: str | None = None
    object_count: int | None = None
    size: int | None = None


@dataclass
class Bucket:
    name: str
    provider: str
    source: str
    probe: Probe


@dataclass
class Candidates:
    items: list[Candidate] = field(default_factory=list)
    capped: bool = False


# ---------- candidate names ----------


def _clean_name(value: str) -> str:
    return "".join(c for c in value.strip().lower() if c.isalnum() or c in "-.")


def clean_words(values: list[str], *, max_length: int) -> list[str]:
    seen: list[str] = []
    for raw in values:
        value = "".join(c for c in str(raw).strip().lower() if c.isalnum() or c == "-")
        if value and len(value) <= max_length and value not in seen:
            seen.append(value)
    return seen


def guessed_names(label: str, words: list[str]) -> list[str]:
    """The label on its own and joined to each word with no, dot and dash."""
    out = [label]
    for word in words:
        out.extend(
            (
                f"{label}{word}",
                f"{label}-{word}",
                f"{label}.{word}",
                f"{word}{label}",
                f"{word}-{label}",
                f"{word}.{label}",
            )
        )
    return out


def candidates(
    *,
    label: str,
    hostnames: list[str],
    referenced: list[Candidate],
    words: list[str],
    guess: bool,
    cap: int = MAX_CANDIDATES,
) -> Candidates:
    """Referenced, then hostname, then guessed names, each kept once at its strongest source."""
    chosen: dict[tuple[str | None, str], Candidate] = {}

    def add(name: str, source: str, provider: str | None) -> None:
        name = _clean_name(name)
        if not name or len(name) > MAX_NAME_LENGTH or not _LABEL.match(name):
            return
        key = (provider, name)
        if key not in chosen:
            chosen[key] = Candidate(name=name, source=source, provider=provider)

    for item in referenced:
        add(item.name, Source.REFERENCED.value, item.provider)
    for host in hostnames:
        add(host, Source.HOSTNAME.value, None)
    if guess:
        for name in guessed_names(label, words):
            add(name, Source.GUESSED.value, None)

    items = list(chosen.values())
    capped = len(items) > cap
    return Candidates(items=items[:cap], capped=capped)


# ---------- referenced buckets in what the scan already read ----------

_HOST_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"^(?P<name>[a-z0-9.-]+)\.s3[.-][a-z0-9-]*\.?amazonaws\.com$"),
        Provider.AWS_S3.value,
    ),
    (re.compile(r"^(?P<name>[a-z0-9.-]+)\.s3\.amazonaws\.com$"), Provider.AWS_S3.value),
    (
        re.compile(r"^(?P<name>[a-z0-9.-]+)\.storage\.googleapis\.com$"),
        Provider.GCS.value,
    ),
    (
        re.compile(r"^(?P<name>[a-z0-9-]+)\.blob\.core\.windows\.net$"),
        Provider.AZURE_BLOB.value,
    ),
    (
        re.compile(r"^(?P<name>[a-z0-9-]+)\.firebaseio\.com$"),
        Provider.FIREBASE_RTDB.value,
    ),
    (
        re.compile(r"^(?P<name>[a-z0-9-]+)\.firebasedatabase\.app$"),
        Provider.FIREBASE_RTDB.value,
    ),
    (
        re.compile(r"^(?P<name>[a-z0-9.-]+)\.[a-z0-9-]+\.digitaloceanspaces\.com$"),
        Provider.DO_SPACES.value,
    ),
)
_PATH_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^storage\.googleapis\.com$"), Provider.GCS.value),
    (re.compile(r"^s3\.amazonaws\.com$"), Provider.AWS_S3.value),
    (re.compile(r"^s3[.-][a-z0-9-]+\.amazonaws\.com$"), Provider.AWS_S3.value),
)
_R2 = re.compile(
    r"\bpub-[a-f0-9]{32}\.r2\.dev\b|\b[a-z0-9-]+\.r2\.cloudflarestorage\.com\b"
)


def _from_host(host: str) -> Candidate | None:
    host = host.strip().lower().rstrip(".")
    for rule, provider in _HOST_RULES:
        match = rule.match(host)
        if match:
            return Candidate(
                name=match.group("name"),
                source=Source.REFERENCED.value,
                provider=provider,
            )
    return None


def referenced_in(
    *, hosts: list[str], cnames: list[str], urls: list[str]
) -> list[Candidate]:
    """Storage buckets a hostname, CNAME or URL the scan read already points at."""
    found: dict[tuple[str, str], Candidate] = {}

    def keep(item: Candidate | None) -> None:
        if item is not None:
            found.setdefault((item.provider or "", item.name), item)

    for host in hosts:
        keep(_from_host(host))
    for cname in cnames:
        keep(_from_host(cname))
    for raw in urls:
        try:
            parts = urlsplit(raw if "://" in raw else f"//{raw}")
        except ValueError:
            continue
        host = (parts.hostname or "").lower()
        if not host:
            continue
        direct = _from_host(host)
        if direct is not None:
            keep(direct)
            continue
        first = parts.path.lstrip("/").split("/", 1)[0]
        for rule, provider in _PATH_RULES:
            if rule.match(host) and first:
                keep(
                    Candidate(
                        name=first, source=Source.REFERENCED.value, provider=provider
                    )
                )
                break
        if _R2.search(raw):
            keep(
                Candidate(
                    name=host,
                    source=Source.REFERENCED.value,
                    provider=Provider.R2.value,
                )
            )
    return list(found.values())


# ---------- provider probes ----------


def _listing(response: httpx.Response) -> tuple[int | None, int | None]:
    body = b""
    for chunk in response.iter_bytes():
        body += chunk
        if len(body) >= LISTING_MAX_BYTES:
            break
    count = len(_CONTENTS.findall(body)) or None
    return count, None


def _probe_s3(client: httpx.Client, name: str) -> Probe | None:
    url = f"https://{name}.s3.amazonaws.com/"
    with client.stream("GET", url) as response:
        region = response.headers.get("x-amz-bucket-region")
        if response.status_code == HTTPStatus.OK:
            count, size = _listing(response)
            return Probe(Access.LISTABLE.value, url, region, count, size)
        if response.status_code == HTTPStatus.FORBIDDEN:
            return Probe(Access.PROTECTED.value, url, region)
        if (
            response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
            and b"SlowDown" in response.read()
        ):
            raise ThrottledError
    return None


def _probe_gcs(client: httpx.Client, name: str) -> Probe | None:
    url = f"https://storage.googleapis.com/{name}/"
    with client.stream("GET", url) as response:
        if response.status_code == HTTPStatus.OK:
            count, size = _listing(response)
            return Probe(Access.LISTABLE.value, url, None, count, size)
        if response.status_code == HTTPStatus.FORBIDDEN:
            return Probe(Access.PROTECTED.value, url)
        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            raise ThrottledError
    return None


def _probe_azure(client: httpx.Client, name: str) -> Probe | None:
    url = f"https://{name}.blob.core.windows.net/{name}?restype=container&comp=list"
    try:
        with client.stream("GET", url) as response:
            display = f"https://{name}.blob.core.windows.net/{name}"
            if response.status_code == HTTPStatus.OK:
                count, size = _listing(response)
                return Probe(Access.LISTABLE.value, display, None, count, size)
            if response.status_code in (HTTPStatus.FORBIDDEN, HTTPStatus.CONFLICT):
                return Probe(Access.PROTECTED.value, display)
    except httpx.ConnectError:
        return None
    return None


def _probe_firebase(client: httpx.Client, name: str) -> Probe | None:
    url = f"https://{name}.firebaseio.com/.json"
    try:
        response = client.get(url)
    except httpx.ConnectError:
        return None
    if response.status_code == HTTPStatus.OK:
        return Probe(Access.READABLE.value, url)
    if response.status_code in (
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.PAYMENT_REQUIRED,
        HTTPStatus.LOCKED,
    ):
        return Probe(Access.PROTECTED.value, url)
    return None


def _probe_do(client: httpx.Client, name: str) -> Probe | None:
    for region in DO_REGIONS:
        url = f"https://{name}.{region}.digitaloceanspaces.com/"
        try:
            with client.stream("GET", url) as response:
                if response.status_code == HTTPStatus.OK:
                    count, size = _listing(response)
                    return Probe(Access.LISTABLE.value, url, region, count, size)
                if response.status_code == HTTPStatus.FORBIDDEN:
                    return Probe(Access.PROTECTED.value, url, region)
        except httpx.ConnectError:
            continue
    return None


def _probe_r2(client: httpx.Client, name: str) -> Probe | None:
    url = name if "://" in name else f"https://{name}/"
    try:
        response = client.get(url)
    except httpx.HTTPError:
        return None
    if response.status_code < HTTPStatus.BAD_REQUEST:
        return Probe(Access.READABLE.value, url)
    if response.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
        return Probe(Access.PROTECTED.value, url)
    return None


PROBES = {
    Provider.AWS_S3.value: _probe_s3,
    Provider.GCS.value: _probe_gcs,
    Provider.AZURE_BLOB.value: _probe_azure,
    Provider.FIREBASE_RTDB.value: _probe_firebase,
    Provider.DO_SPACES.value: _probe_do,
    Provider.R2.value: _probe_r2,
}


def probe(client: httpx.Client, candidate: Candidate) -> list[Bucket]:
    """Probe the candidate's provider, or every guessable provider when it names none."""
    providers = (
        [candidate.provider] if candidate.provider else list(GUESSABLE_PROVIDERS)
    )
    out: list[Bucket] = []
    for provider in providers:
        fn = PROBES.get(provider)
        if fn is None:
            continue
        result = fn(client, candidate.name)
        if result is not None and result.access in STORED_ACCESS:
            out.append(Bucket(candidate.name, provider, candidate.source, result))
    return out


def client(proxy_url: str | None, timeout: int) -> httpx.Client:
    return httpx.Client(
        timeout=timeout,
        follow_redirects=False,
        verify=False,  # noqa: S501
        proxy=proxy_url or None,
        headers={"User-Agent": PROBE_USER_AGENT},
        limits=httpx.Limits(max_keepalive_connections=0),
    )


# ---------- rows ----------


def replace_rows(
    session: Session,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
    buckets: list[Bucket],
) -> int:
    """Replace the scan's buckets, carrying each name's first sighting forward."""
    keys = [(b.provider, b.name) for b in buckets]
    earlier = dict(
        session.execute(
            select(
                func.concat(CloudBucket.provider, "|", CloudBucket.name),
                func.min(CloudBucket.first_seen),
            )
            .where(
                CloudBucket.target_id == target_id,
                CloudBucket.scan_id != scan_id,
                func.concat(CloudBucket.provider, "|", CloudBucket.name).in_(
                    [f"{p}|{n}" for p, n in keys] or [""]
                ),
            )
            .group_by(func.concat(CloudBucket.provider, "|", CloudBucket.name))
        ).all()
    )
    session.execute(delete(CloudBucket).where(CloudBucket.scan_id == scan_id))
    now = utc_now()
    for bucket in buckets:
        session.add(
            CloudBucket(
                scan_id=scan_id,
                target_id=target_id,
                project_id=project_id,
                name=bucket.name,
                provider=bucket.provider,
                url=strip_nul(bucket.probe.url)[:MAX_URL_LENGTH],
                source=bucket.source,
                access=bucket.probe.access,
                region=bucket.probe.region,
                object_count=bucket.probe.object_count,
                size=bucket.probe.size,
                first_seen=earlier.get(f"{bucket.provider}|{bucket.name}") or now,
                discovered_at=now,
            )
        )
    session.flush()
    return len(buckets)


def is_owned(source: str) -> bool:
    return source in OWNED_SOURCES
