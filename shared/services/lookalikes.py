"""Permutations, classification and the one writer of lookalike_domains."""

from __future__ import annotations

import html
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime

import dnstwist
import ppdeep
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from shared.definitions.domains import registrable_domain
from shared.definitions.lookalikes import (
    LIVE_BELOW,
    MAX_DOMAIN_LENGTH,
    MAX_RECORDS,
    MAX_REGISTRAR_LENGTH,
    MAX_TITLE_LENGTH,
    MAX_URL_LENGTH,
    NO_MAIL,
    PARKING_NAMESERVERS,
    PARKING_NS_NEEDS_PAGE,
    PARKING_PHRASES,
    SALE_HOSTS,
    SIMILAR_AT,
    SWAP_TLDS,
    LinkReason,
    Verdict,
)
from shared.models.lookalike import LookalikeDomain
from shared.utils.datetime import utc_now
from shared.utils.infra import is_shared_nameserver
from shared.utils.text import strip_control, strip_nul

_ORIGINAL = "*original"
_TITLE = re.compile(rb"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_ATTR = re.compile(rb'(action|src|href)=".+?"', re.IGNORECASE)
_CSS_URL = re.compile(rb"url\(.+?\)", re.IGNORECASE)


@dataclass
class Records:
    a: list[str] = field(default_factory=list)
    aaaa: list[str] = field(default_factory=list)
    mx: list[str] = field(default_factory=list)
    ns: list[str] = field(default_factory=list)

    @property
    def registered(self) -> bool:
        return bool(self.a or self.aaaa or self.mx or self.ns)

    @property
    def addressed(self) -> bool:
        return bool(self.a or self.aaaa)

    @property
    def addresses(self) -> list[str]:
        return [*self.a, *self.aaaa]


@dataclass
class Page:
    status: int | None = None
    final_url: str | None = None
    title: str | None = None
    body: bytes = b""


@dataclass
class Lookalike:
    domain: str
    technique: str
    records: Records
    page: Page | None = None
    similarity: int | None = None
    parked: bool = False
    link_reason: str | None = None
    verdict: str = Verdict.REGISTERED.value
    registered_at: datetime | None = None
    registrar: str | None = None


def permutations(
    apex: str, *, tld_swap: bool, words: list[str], cap: int
) -> list[tuple[str, str]]:
    """(domain, technique) for every permutation of the apex, the apex excluded."""
    swap = list(SWAP_TLDS) if tld_swap else []
    fuzzer = dnstwist.Fuzzer(apex, dictionary=words, tld_dictionary=swap)
    fuzzer.generate()
    out: dict[str, str] = {}
    for perm in fuzzer.domains:
        name = str(perm["domain"]).lower().rstrip(".")
        technique = str(perm["fuzzer"])
        if technique == _ORIGINAL or name == apex or len(name) > MAX_DOMAIN_LENGTH:
            continue
        out.setdefault(name, technique)
    ranked = sorted(out.items(), key=lambda item: (item[1] == "homoglyph", item[0]))
    return ranked[:cap]


def display(domain: str) -> str:
    try:
        return domain.encode("ascii").decode("idna")
    except UnicodeError:
        return domain


def title_of(body: bytes) -> str | None:
    match = _TITLE.search(body[:200_000])
    if not match:
        return None
    text = " ".join(
        html.unescape(match.group(1).decode("utf-8", errors="replace")).split()
    )
    text = strip_control(text)
    return text[:MAX_TITLE_LENGTH] or None


def normalized(body: bytes) -> bytes:
    content = b" ".join(body.split())
    content = _ATTR.sub(lambda m: m.group(1) + b'=""', content)
    return _CSS_URL.sub(b"url()", content)


def fuzzy_hash(body: bytes) -> str | None:
    if not body:
        return None
    value = ppdeep.hash(normalized(body))
    return None if value in (None, "3::") else value


def similarity(original: str | None, body: bytes) -> int | None:
    if not original:
        return None
    current = fuzzy_hash(body)
    if current is None:
        return None
    return int(ppdeep.compare(original, current))


def _host(url: str) -> str:
    return url.split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0].lower()


def receives_mail(records: Records) -> bool:
    return any(
        mx.strip(". ").lower() not in NO_MAIL and "." in mx.strip(". ")
        for mx in records.mx
    )


def _zone(host: str) -> str:
    return registrable_domain(host.strip().lower().rstrip(".")) or host


def parked(records: Records, page: Page | None) -> bool:
    zones = {_zone(ns) for ns in records.ns}
    text = b""
    if page is not None:
        text = ((page.title or "").encode() + b" " + page.body[:100_000]).lower()
    by_page = any(p.encode() in text for p in PARKING_PHRASES)
    if (
        page is not None
        and page.final_url
        and _zone(_host(page.final_url)) in SALE_HOSTS
    ):
        return True
    for zone in zones & set(PARKING_NAMESERVERS):
        if zone not in PARKING_NS_NEEDS_PAGE or by_page:
            return True
    return by_page


def link_reason(
    *,
    apex: str,
    records: Records,
    page: Page | None,
    apex_ns: set[str],
    tracked: bool,
) -> str | None:
    if tracked:
        return LinkReason.TARGET.value
    if page is not None and page.final_url:
        host = _host(page.final_url)
        if host and _zone(host) == _zone(apex):
            return LinkReason.REDIRECT.value
    own = {
        ns
        for ns in (n.strip().lower().rstrip(".") for n in records.ns)
        if not is_shared_nameserver(ns)
    }
    if own and own & apex_ns:
        return LinkReason.NAMESERVERS.value
    return None


def verdict(item: Lookalike) -> str:
    if item.link_reason:
        return Verdict.LINKED.value
    if item.similarity is not None and item.similarity >= SIMILAR_AT:
        return Verdict.SIMILAR_PAGE.value
    if receives_mail(item.records):
        return Verdict.MAIL.value
    if item.parked:
        return Verdict.PARKED.value
    page = item.page
    if page is not None and page.status is not None and page.status < LIVE_BELOW:
        return Verdict.LIVE.value
    return Verdict.REGISTERED.value


def _clip(values: list[str]) -> list[str]:
    return [strip_nul(v)[:MAX_DOMAIN_LENGTH] for v in values[:MAX_RECORDS]]


def replace_rows(
    session: Session,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
    apex: str,
    items: list[Lookalike],
) -> int:
    """Replace the scan's rows, carrying each domain's first sighting forward."""
    earlier = dict(
        session.execute(
            select(LookalikeDomain.domain, func.min(LookalikeDomain.first_seen))
            .where(
                LookalikeDomain.target_id == target_id,
                LookalikeDomain.scan_id != scan_id,
                LookalikeDomain.domain.in_([i.domain for i in items] or [""]),
            )
            .group_by(LookalikeDomain.domain)
        ).all()
    )
    session.execute(delete(LookalikeDomain).where(LookalikeDomain.scan_id == scan_id))
    now = utc_now()
    for item in items:
        page = item.page
        session.add(
            LookalikeDomain(
                scan_id=scan_id,
                target_id=target_id,
                project_id=project_id,
                apex=apex,
                domain=item.domain,
                display=display(item.domain)[:MAX_DOMAIN_LENGTH],
                technique=item.technique,
                verdict=item.verdict,
                link_reason=item.link_reason,
                a=_clip(item.records.a),
                aaaa=_clip(item.records.aaaa),
                mx=_clip(item.records.mx),
                ns=_clip(item.records.ns),
                parked=item.parked,
                http_status=page.status if page else None,
                final_url=strip_nul(page.final_url)[:MAX_URL_LENGTH]
                if page and page.final_url
                else None,
                title=page.title if page else None,
                similarity=item.similarity,
                registered_at=item.registered_at,
                registrar=strip_control(item.registrar)[:MAX_REGISTRAR_LENGTH]
                if item.registrar
                else None,
                first_seen=earlier.get(item.domain) or now,
                discovered_at=now,
            )
        )
    session.flush()
    return len(items)
