"""External resources embedded in stored pages whose domain is now buyable."""

from __future__ import annotations

import random
import re
import socket
import struct
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shared.definitions.broken_links import (
    BODY_SCAN_BYTES,
    KIND_RANK,
    KIND_SEVERITY,
    MAX_DOMAINS,
    MAX_PAGES,
    RESOLVE_QUORUM,
    RESOLVE_WORKERS,
    RESOLVERS,
    LinkKind,
)
from shared.definitions.domains import (
    IGNORED_DOMAINS,
    is_public_tld,
    owning_zone,
    registrable_domain,
    target_zone,
)
from shared.definitions.estate import provider_of
from shared.models.http_asset import HttpAsset

_STREAM_BATCH = 200
_TIMEOUT = 2.5
_HEADER = 12
_RCODE_MASK = 0x000F
_RCODE_NXDOMAIN = 3
_TYPE_A = 1
_MAX_EXAMPLES = 5
_TAG_SOURCES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        LinkKind.SCRIPT.value,
        re.compile(r"<script\b[^>]*\bsrc\s*=\s*[\"']([^\"']+)", re.I),
    ),
    (
        LinkKind.IFRAME.value,
        re.compile(r"<iframe\b[^>]*\bsrc\s*=\s*[\"']([^\"']+)", re.I),
    ),
    (LinkKind.IMAGE.value, re.compile(r"<img\b[^>]*\bsrc\s*=\s*[\"']([^\"']+)", re.I)),
)
_LINK_TAG = re.compile(r"<link\b[^>]*>", re.I)
_HREF = re.compile(r"\bhref\s*=\s*[\"']([^\"']+)", re.I)
_REL = re.compile(r"\brel\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s\"'>]+))", re.I)
_AS = re.compile(r"\bas\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s\"'>]+))", re.I)
_ICON_RELS = frozenset({"icon", "apple-touch-icon", "apple-touch-icon-precomposed"})
_ABSOLUTE = re.compile(r"^https?://", re.I)


@dataclass
class BrokenLink:
    resource_host: str
    domain: str
    kind: str
    severity: str
    page_host: str
    page_url: str
    page_scheme: str | None
    page_port: int | None
    pages: int = 1
    examples: list[str] = field(default_factory=list)


def _external_host(value: str) -> str | None:
    value = value.strip()
    if value.startswith("//"):
        value = "https:" + value
    if not _ABSOLUTE.match(value):
        return None
    try:
        host = (urlsplit(value).hostname or "").lower().strip(".")
    except ValueError:
        return None
    return host or None


def _attr(pattern: re.Pattern[str], tag: str) -> str:
    match = pattern.search(tag)
    if match is None:
        return ""
    return next(value for value in match.groups() if value is not None).strip().lower()


def _link_kind(tag: str) -> str:
    rel = set(_attr(_REL, tag).split())
    if "stylesheet" in rel:
        return LinkKind.STYLESHEET.value
    if "modulepreload" in rel or ("preload" in rel and _attr(_AS, tag) == "script"):
        return LinkKind.SCRIPT.value
    if rel & _ICON_RELS:
        return LinkKind.IMAGE.value
    return LinkKind.LINK.value


def _sources(body: str):
    for kind, pattern in _TAG_SOURCES:
        for raw in pattern.findall(body):
            yield kind, raw
    for tag in _LINK_TAG.findall(body):
        href = _HREF.search(tag)
        if href:
            yield _link_kind(tag), href.group(1)


def _resources(body: str) -> dict[str, str]:
    """The strongest tag each external host appears as on one page."""
    found: dict[str, str] = {}
    for kind, raw in _sources(body):
        host = _external_host(raw)
        if host is None:
            continue
        if host not in found or KIND_RANK[kind] > KIND_RANK[found[host]]:
            found[host] = kind
    return found


def _packet(name: str) -> bytes:
    header = struct.pack("!HHHHHH", random.randint(0, 65535), 0x0100, 1, 0, 0, 0)  # noqa: S311
    labels = [part for part in name.strip(".").split(".") if part]
    try:
        question = b"".join(
            bytes([len(label.encode("idna"))]) + label.encode("idna")
            for label in labels
        )
    except UnicodeError:
        return b""
    return header + question + b"\x00" + struct.pack("!HH", _TYPE_A, 1)


def _rcode(name: str, server: str) -> int | None:
    packet = _packet(name)
    if not packet:
        return None
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(_TIMEOUT)
    try:
        sock.sendto(packet, (server, 53))
        data, _ = sock.recvfrom(4096)
    except OSError:
        return None
    finally:
        sock.close()
    if len(data) < _HEADER or data[:2] != packet[:2]:
        return None
    return struct.unpack("!H", data[2:4])[0] & _RCODE_MASK


def is_unregistered(domain: str, resolvers: tuple[str, ...] = RESOLVERS) -> bool:
    """The apex does not exist at a quorum of resolvers and none of them disagree."""
    nxdomain = 0
    answered = 0
    for server in resolvers:
        rcode = _rcode(domain, server)
        if rcode is None:
            continue
        answered += 1
        if rcode == _RCODE_NXDOMAIN:
            nxdomain += 1
        else:
            return False
    return answered >= RESOLVE_QUORUM and nxdomain == answered


def dangling(session: Session, scan_id: UUID, root: str) -> list[BrokenLink]:
    """External resources whose registrable domain is buyable, worst tag first."""
    own = target_zone(root)
    candidates: dict[tuple[str, str], BrokenLink] = {}
    page_ids = list(
        session.scalars(
            select(HttpAsset.id)
            .where(HttpAsset.scan_id == scan_id, HttpAsset.response_body != "")
            .order_by(HttpAsset.host, HttpAsset.url, HttpAsset.id)
            .limit(MAX_PAGES)
        )
    )
    for start in range(0, len(page_ids), _STREAM_BATCH):
        chunk = page_ids[start : start + _STREAM_BATCH]
        position = {page_id: index for index, page_id in enumerate(chunk)}
        batch = session.execute(
            select(
                HttpAsset.id,
                HttpAsset.host,
                HttpAsset.url,
                HttpAsset.scheme,
                HttpAsset.port,
                func.left(HttpAsset.response_body, BODY_SCAN_BYTES),
            ).where(HttpAsset.id.in_(chunk))
        )
        for _id, host, url, scheme, port, body in sorted(
            batch, key=lambda row: position[row[0]]
        ):
            for resource_host, kind in _resources(body).items():
                domain = registrable_domain(resource_host)
                if not _worth_checking(domain, own):
                    continue
                key = (resource_host, kind)
                existing = candidates.get(key)
                if existing is None:
                    candidates[key] = BrokenLink(
                        resource_host=resource_host,
                        domain=domain,
                        kind=kind,
                        severity="",
                        page_host=host or "",
                        page_url=url or "",
                        page_scheme=scheme,
                        page_port=port,
                        examples=[url] if url else [],
                    )
                else:
                    existing.pages += 1
                    if (
                        url
                        and len(existing.examples) < _MAX_EXAMPLES
                        and url not in existing.examples
                    ):
                        existing.examples.append(url)

    weight: dict[str, tuple[int, int]] = {}
    for link in candidates.values():
        rank, pages = weight.get(link.domain, (0, 0))
        weight[link.domain] = (max(rank, KIND_RANK[link.kind]), pages + link.pages)
    order = sorted(
        weight, key=lambda domain: (-weight[domain][0], -weight[domain][1], domain)
    )
    buyable = _resolve_buyable(order[:MAX_DOMAINS])
    return _ranked([link for link in candidates.values() if link.domain in buyable])


def _worth_checking(domain: str, own: str) -> bool:
    return bool(
        domain
        and is_public_tld(domain)
        and owning_zone(domain, {own}) is None
        and domain not in IGNORED_DOMAINS
        and provider_of(domain) is None
    )


def _resolve_buyable(domains: list[str]) -> set[str]:
    if not domains:
        return set()
    workers = min(RESOLVE_WORKERS, len(domains))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        verdicts = pool.map(is_unregistered, domains)
    return {
        domain for domain, buyable in zip(domains, verdicts, strict=True) if buyable
    }


def _ranked(links: list[BrokenLink]) -> list[BrokenLink]:
    for link in links:
        link.severity = KIND_SEVERITY[link.kind]
    return sorted(links, key=lambda link: (-KIND_RANK[link.kind], link.resource_host))
