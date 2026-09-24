"""Judge which owned names are answered by a server that does not host them."""

from __future__ import annotations

import ipaddress
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shared.definitions.correlation import MIN_BODY_BYTES
from shared.definitions.domains import IGNORED_DOMAINS, registrable_domain
from shared.definitions.estate import provider_of
from shared.definitions.name_ownership import (
    ALIAS_OVERLAP,
    BODY_SCAN_BYTES,
    LOCAL_SUFFIXES,
    MAX_CERT_DOMAINS,
    MIN_ALIAS_LABEL,
    MIN_EVIDENCE,
    MIN_LINKS,
    ClaimEvidence,
    NameClaim,
)
from shared.models.http_asset import HttpAsset
from shared.models.target import Target
from shared.utils.infra import generic_page
from shared.utils.net import cert_covers

_LINK = re.compile(r"""(?:href|src|action)\s*=\s*["']https?://([a-z0-9.-]+)""", re.I)
_HTTP_OK = 200
_HTTP_REDIRECT = 300
_HTTPS = "https"


@dataclass
class Asset:
    host: str
    url: str
    ip: str | None
    port: int | None
    scheme: str | None
    status_code: int | None
    title: str | None
    final_url: str | None
    location: str | None
    tls_subject_cn: str | None
    tls_sans: list[str]
    is_cdn: bool
    content_hash: str | None
    content_length: int | None
    asn_org: str | None
    body: str | None


@dataclass
class Claim:
    kind: str
    host: str
    url: str
    ip: str | None
    port: int | None
    scheme: str | None
    domain: str
    title: str | None
    asn_org: str | None
    evidence: list[tuple[str, str]] = field(default_factory=list)
    siblings: int = 0


def _is_address(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def _url_host(url: str | None) -> str:
    if not url:
        return ""
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _inside(name: str, root: str) -> bool:
    return name == root or name.endswith(f".{root}")


def _grams(label: str) -> set[str]:
    text = re.sub(r"[^a-z0-9]", "", label.lower())
    return {text[i : i + 2] for i in range(len(text) - 1)}


def _alias(host: str, domain: str, root: str, title: str | None) -> bool:
    """Whether the domain reads as the owner's own other name."""
    theirs = domain.split(".", maxsplit=1)[0]
    brand = registrable_domain(root).split(".")[0]
    if len(brand) >= MIN_ALIAS_LABEL and (
        brand in theirs or brand in (title or "").lower()
    ):
        return True
    ours = [
        label
        for label in host[: -len(root)].strip(".").split(".")
        if label and label != "www"
    ]
    for label in ours:
        if len(label) >= MIN_ALIAS_LABEL and (label in theirs or theirs in label):
            return True
        a, b = _grams(label), _grams(theirs)
        if a and b and len(a & b) / len(a | b) >= ALIAS_OVERLAP:
            return True
    return False


def _foreign(domain: str, root: str, owned: set[str]) -> bool:
    if not domain or domain.rsplit(".", 1)[-1] in LOCAL_SUFFIXES:
        return False
    if _inside(domain, root) or any(_inside(domain, r) for r in owned):
        return False
    if domain in IGNORED_DOMAINS:
        return False
    return not (provider_of(domain) or provider_of(f"www.{domain}"))


def _evidence(asset: Asset, default: Asset | None) -> dict[str, list[tuple[str, str]]]:
    found: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for url in (asset.final_url, asset.location):
        domain = registrable_domain(_url_host(url))
        if domain and all(k != ClaimEvidence.REDIRECT.value for k, _ in found[domain]):
            found[domain].append((ClaimEvidence.REDIRECT.value, url or ""))
    if asset.tls_subject_cn and not cert_covers(
        asset.host, asset.tls_subject_cn, asset.tls_sans
    ):
        names = [n for n in (asset.tls_subject_cn, *asset.tls_sans) if n]
        domains = {registrable_domain(str(n).lower().removeprefix("*.")) for n in names}
        domains.discard("")
        if len(domains) <= MAX_CERT_DOMAINS:
            for domain in domains:
                found[domain].append(
                    (ClaimEvidence.CERTIFICATE.value, asset.tls_subject_cn)
                )
    if asset.body:
        links = Counter(
            registrable_domain(h.lower()) for h in _LINK.findall(asset.body)
        )
        links.pop("", None)
        if links:
            domain, count = links.most_common(1)[0]
            if count >= MIN_LINKS:
                found[domain].append((ClaimEvidence.LINKS.value, str(count)))
    if (
        default is not None
        and default.content_hash
        and default.content_hash == asset.content_hash
        and (asset.content_length or 0) >= MIN_BODY_BYTES
    ):
        for items in found.values():
            items.append((ClaimEvidence.ADDRESS_DEFAULT.value, default.host))
    return found


def _served(asset: Asset) -> bool:
    status = asset.status_code
    return (
        status is not None
        and _HTTP_OK <= status < _HTTP_REDIRECT
        and generic_page(asset.title, [status]) is None
    )


def _judge_one(
    asset: Asset, default: Asset | None, root: str, owned: set[str]
) -> Claim | None:
    host = asset.host.lower()
    if asset.is_cdn or _is_address(host) or not _inside(host, root):
        return None
    if asset.body and root in asset.body.lower():
        return None
    best: Claim | None = None
    for domain, items in _evidence(asset, default).items():
        if not _foreign(domain, root, owned) or _alias(host, domain, root, asset.title):
            continue
        kinds = {kind for kind, _ in items}
        named = kinds & {ClaimEvidence.REDIRECT.value, ClaimEvidence.CERTIFICATE.value}
        if not named or len(kinds) < MIN_EVIDENCE:
            continue
        if (
            asset.body is None
            and not {
                ClaimEvidence.REDIRECT.value,
                ClaimEvidence.CERTIFICATE.value,
            }
            <= kinds
        ):
            continue
        if _served(asset) and kinds - {ClaimEvidence.CERTIFICATE.value}:
            kind = NameClaim.FOREIGN_SITE.value
        elif ClaimEvidence.ADDRESS_DEFAULT.value in kinds or (
            domain.rsplit(".", 1)[-1] != root.rsplit(".", 1)[-1]
        ):
            kind = NameClaim.UNHOSTED.value
        else:
            continue
        claim = Claim(
            kind=kind,
            host=host,
            url=asset.url,
            ip=asset.ip,
            port=asset.port,
            scheme=asset.scheme,
            domain=domain,
            title=asset.title,
            asn_org=asset.asn_org,
            evidence=items,
        )
        if best is None or _rank(claim) > _rank(best):
            best = claim
    return best


def _rank(claim: Claim) -> tuple[int, int, bool]:
    return (
        claim.kind == NameClaim.FOREIGN_SITE.value,
        len({kind for kind, _ in claim.evidence}),
        claim.scheme == _HTTPS,
    )


def judge(assets: list[Asset], root: str, owned: set[str]) -> list[Claim]:
    """One claim per owned name, strongest first."""
    root = root.lower().rstrip(".")
    defaults = {
        (a.ip, a.port): a for a in assets if _is_address(a.host) and a.content_hash
    }
    best: dict[str, Claim] = {}
    for asset in assets:
        claim = _judge_one(asset, defaults.get((asset.ip, asset.port)), root, owned)
        if claim is None:
            continue
        current = best.get(claim.host)
        if current is None or _rank(claim) > _rank(current):
            best[claim.host] = claim
    claims = list(best.values())
    together = Counter((c.ip, c.domain) for c in claims)
    for claim in claims:
        claim.siblings = together[(claim.ip, claim.domain)] - 1
    claims.sort(key=lambda c: (c.kind != NameClaim.FOREIGN_SITE.value, c.host))
    return claims


def claims(session: Session, scan_id: UUID, root: str, project_id: UUID) -> list[Claim]:
    """Judge a scan's web assets against the target root and every other target."""
    owned = {
        value.lower()
        for value in session.execute(
            select(Target.target_value).where(Target.project_id == project_id)
        ).scalars()
    }
    owned.discard(root.lower())
    rows = session.execute(
        select(
            HttpAsset.host,
            HttpAsset.url,
            HttpAsset.ip,
            HttpAsset.port,
            HttpAsset.scheme,
            HttpAsset.status_code,
            HttpAsset.title,
            HttpAsset.final_url,
            HttpAsset.location,
            HttpAsset.tls_subject_cn,
            HttpAsset.tls_sans,
            HttpAsset.is_cdn,
            HttpAsset.content_hash,
            HttpAsset.content_length,
            HttpAsset.asn_org,
            func.left(HttpAsset.response_body, BODY_SCAN_BYTES),
        ).where(HttpAsset.scan_id == scan_id)
    ).all()
    assets = [
        Asset(
            host=r[0] or "",
            url=r[1] or "",
            ip=r[2],
            port=r[3],
            scheme=r[4],
            status_code=r[5],
            title=r[6],
            final_url=r[7],
            location=r[8],
            tls_subject_cn=r[9],
            tls_sans=[str(s) for s in (r[10] or [])],
            is_cdn=bool(r[11]),
            content_hash=r[12],
            content_length=r[13],
            asn_org=r[14],
            body=r[15],
        )
        for r in rows
        if r[0]
    ]
    return judge(assets, root, owned)
