"""Correlate service fingerprints across the CDN boundary to find reachable origins."""

from __future__ import annotations

import ipaddress
from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.ports import SENSITIVE_PORTS
from shared.models.http_asset import HttpAsset
from shared.models.port import Port
from shared.models.scan_correlation import (
    OriginEvidence,
    OriginExposure,
    OriginFinding,
    OriginSample,
)

# a shared fingerprint is only proof if it is specific to the application
FINGERPRINTS: tuple[tuple[str, str, int], ...] = (
    ("tls_fingerprint", "TLS certificate", 3),
    ("content_hash", "Response body", 2),
    ("favicon_hash", "Favicon", 2),
    ("header_hash", "Response headers", 1),
)
HIGH_CONFIDENCE = 3
MEDIUM_CONFIDENCE = 2
# a fingerprint shared by more hosts than this is a platform default, not an application
MAX_SHARED_HOSTS = 60
# discriminating power falls off with reach: a body hash on two hosts identifies an
# application, a wildcard certificate on thirty only identifies the organisation
NARROW_REACH = 3
BROAD_REACH = 12
# an error or near-empty body hashes the same everywhere; it proves nothing
MIN_BODY_BYTES = 512
HTTP_OK = 200
HTTP_CLIENT_ERROR = 400
MAX_FINDINGS = 20
MAX_FRONTED_SHOWN = 6
HTTPS_PORT = 443

ORIGIN_EXPOSED = "origin_exposed"
DEFAULT_VHOST = "default_vhost"

_COLUMNS = (
    HttpAsset.host,
    HttpAsset.url,
    HttpAsset.ip,
    HttpAsset.port,
    HttpAsset.status_code,
    HttpAsset.title,
    HttpAsset.webserver,
    HttpAsset.is_cdn,
    HttpAsset.cdn_name,
    HttpAsset.asn_org,
    HttpAsset.screenshot_path,
    HttpAsset.content_length,
    HttpAsset.tls_fingerprint,
    HttpAsset.content_hash,
    HttpAsset.favicon_hash,
    HttpAsset.header_hash,
)


@dataclass
class _Asset:
    host: str
    url: str
    ip: str | None
    port: int
    status_code: int | None
    title: str | None
    webserver: str | None
    is_cdn: bool
    cdn_name: str | None
    asn_org: str | None
    screenshot_path: str | None
    content_length: int | None
    prints: dict[str, str]

    @property
    def is_address(self) -> bool:
        try:
            ipaddress.ip_address(self.host)
        except ValueError:
            return False
        return True

    @property
    def responded(self) -> bool:
        return (
            self.status_code is not None
            and HTTP_OK <= self.status_code < HTTP_CLIENT_ERROR
        )

    def sample(self) -> OriginSample:
        return OriginSample(
            host=self.host,
            url=self.url,
            ip=self.ip,
            port=self.port,
            status_code=self.status_code,
            title=self.title,
            webserver=self.webserver,
            cdn_name=self.cdn_name,
            asn_org=self.asn_org,
            screenshot_path=self.screenshot_path,
        )


class OriginExposureService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def run(self, scan_id: UUID) -> OriginExposure:
        assets = await self._assets(scan_id)
        if not assets:
            return OriginExposure()
        ports = await self._ports(scan_id)
        fronted = [a for a in assets if a.is_cdn]
        findings = self._origins(assets, fronted, ports)
        findings += self._default_vhosts(assets, ports)
        findings = _merge(findings)
        findings.sort(key=lambda f: (f.confidence != "high", -len(f.evidence)))
        return OriginExposure(
            findings=findings[:MAX_FINDINGS],
            probed_addresses=len({a.ip for a in assets if a.is_address and a.ip}),
            fronted_assets=len(fronted),
        )

    async def _assets(self, scan_id: UUID) -> list[_Asset]:
        rows = (
            await self.session.execute(
                select(*_COLUMNS).where(HttpAsset.scan_id == scan_id)
            )
        ).all()
        out: list[_Asset] = []
        for r in rows:
            prints = {
                kind: str(getattr(r, kind))
                for kind, _label, _weight in FINGERPRINTS
                if getattr(r, kind)
            }
            out.append(
                _Asset(
                    host=r.host,
                    url=r.url,
                    ip=r.ip,
                    port=r.port,
                    status_code=r.status_code,
                    title=r.title,
                    webserver=r.webserver,
                    is_cdn=bool(r.is_cdn),
                    cdn_name=r.cdn_name,
                    asn_org=r.asn_org,
                    screenshot_path=r.screenshot_path,
                    content_length=r.content_length,
                    prints=prints,
                )
            )
        return out

    async def _ports(self, scan_id: UUID) -> dict[str, list[int]]:
        rows = (
            await self.session.execute(
                select(Port.ip, Port.number)
                .where(Port.scan_id == scan_id)
                .order_by(Port.ip, Port.number)
            )
        ).all()
        out: dict[str, list[int]] = defaultdict(list)
        for ip, number in rows:
            out[ip].append(int(number))
        return out

    def _index(self, fronted: list[_Asset]) -> dict[tuple[str, str], list[_Asset]]:
        index: dict[tuple[str, str], list[_Asset]] = defaultdict(list)
        for asset in fronted:
            for kind, value in asset.prints.items():
                index[(kind, value)].append(asset)
        # a value on too many hosts is the CDN's own page, not the customer's app
        return {
            key: group for key, group in index.items() if len(group) <= MAX_SHARED_HOSTS
        }

    def _origins(
        self, assets: list[_Asset], fronted: list[_Asset], ports: dict[str, list[int]]
    ) -> list[OriginFinding]:
        index = self._index(fronted)
        findings: list[OriginFinding] = []
        for asset in assets:
            if asset.is_cdn or not asset.responded or not asset.ip:
                continue
            score = 0
            evidence: list[OriginEvidence] = []
            matched: dict[str, _Asset] = {}
            strength: dict[str, int] = {}
            for kind, label, weight in FINGERPRINTS:
                value = asset.prints.get(kind)
                if not value:
                    continue
                if (
                    kind == "content_hash"
                    and (asset.content_length or 0) < MIN_BODY_BYTES
                ):
                    continue
                group = [
                    other
                    for other in index.get((kind, value), ())
                    if other.ip != asset.ip
                ]
                if not group:
                    continue
                reach = len({other.host for other in group})
                score += _weight(weight, reach)
                evidence.append(
                    OriginEvidence(
                        kind=kind,
                        label=label
                        if reach <= BROAD_REACH
                        else f"{label}, shared by {reach} hostnames",
                        value=value[:64],
                    )
                )
                for other in group:
                    matched.setdefault(other.url, other)
                    # the sample shown as proof must be the one that shares the most
                    strength[other.url] = strength.get(other.url, 0) + _weight(
                        weight, reach
                    )
            if score < MEDIUM_CONFIDENCE or not matched:
                continue
            findings.append(
                self._finding(
                    ORIGIN_EXPOSED,
                    "high" if score >= HIGH_CONFIDENCE else "medium",
                    asset,
                    _rank_fronted(list(matched.values()), strength),
                    evidence,
                    ports,
                )
            )
        return findings

    def _default_vhosts(
        self, assets: list[_Asset], ports: dict[str, list[int]]
    ) -> list[OriginFinding]:
        by_endpoint: dict[tuple[str, int], list[_Asset]] = defaultdict(list)
        for asset in assets:
            if asset.ip:
                by_endpoint[(asset.ip, asset.port)].append(asset)
        findings: list[OriginFinding] = []
        for group in by_endpoint.values():
            direct = next((a for a in group if a.is_address and a.responded), None)
            if direct is None or not direct.prints.get("content_hash"):
                continue
            named = [
                a
                for a in group
                if not a.is_address
                and a.responded
                and a.prints.get("content_hash")
                and a.prints["content_hash"] != direct.prints["content_hash"]
            ]
            if not named:
                continue
            findings.append(
                self._finding(
                    DEFAULT_VHOST,
                    "medium",
                    direct,
                    named,
                    [
                        OriginEvidence(
                            kind="content_hash",
                            label="Response body differs",
                            value=direct.prints["content_hash"][:64],
                        )
                    ],
                    ports,
                )
            )
        return findings

    @staticmethod
    def _finding(
        kind: str,
        confidence: str,
        exposed: _Asset,
        others: list[_Asset],
        evidence: list[OriginEvidence],
        ports: dict[str, list[int]],
    ) -> OriginFinding:
        open_ports = ports.get(exposed.ip or "", [])
        # http and https of one hostname are one host, and the count says hostnames
        by_host: dict[str, _Asset] = {}
        for other in others:
            by_host.setdefault(other.host, other)
        unique = list(by_host.values())
        return OriginFinding(
            kind=kind,
            confidence=confidence,
            exposed=exposed.sample(),
            fronted=[other.sample() for other in unique[:MAX_FRONTED_SHOWN]],
            fronted_total=len(unique),
            evidence=evidence,
            open_ports=open_ports,
            sensitive_ports=[p for p in open_ports if p in set(SENSITIVE_PORTS)],
            query=f"ip:{exposed.ip}",
        )


def _weight(base: int, reach: int) -> int:
    if reach <= NARROW_REACH:
        return base
    if reach <= BROAD_REACH:
        return max(1, base - 1)
    return 1


def _rank_fronted(
    assets: list[_Asset], strength: dict[str, int] | None = None
) -> list[_Asset]:
    """Lead with the sample that shares the most identity and can show a screenshot."""
    weights = strength or {}
    return sorted(
        assets,
        key=lambda a: (
            -weights.get(a.url, 0),
            a.screenshot_path is None,
            a.port != HTTPS_PORT,
            a.url,
        ),
    )


def _merge(findings: list[OriginFinding]) -> list[OriginFinding]:
    """One origin per address and hostname; http and https are the same finding."""
    # the origin probe stores the address as a host, so the same origin can surface
    # twice: once by name and once by address. The name is the useful one.
    named = {
        f.exposed.ip
        for f in findings
        if f.kind == ORIGIN_EXPOSED and f.exposed.host != f.exposed.ip
    }
    findings = [
        f
        for f in findings
        if f.kind != ORIGIN_EXPOSED
        or f.exposed.host != f.exposed.ip
        or f.exposed.ip not in named
    ]
    best: dict[tuple[str, str, str], OriginFinding] = {}
    for finding in findings:
        key = (finding.kind, finding.exposed.ip or "", finding.exposed.host)
        current = best.get(key)
        if current is None:
            best[key] = finding
            continue
        keep, drop = (
            (finding, current)
            if (finding.exposed.port == HTTPS_PORT, len(finding.evidence))
            > (current.exposed.port == HTTPS_PORT, len(current.evidence))
            else (current, finding)
        )
        seen = {e.kind for e in keep.evidence}
        keep.evidence.extend(e for e in drop.evidence if e.kind not in seen)
        keep.fronted_total = max(keep.fronted_total, drop.fronted_total)
        if keep.confidence != "high" and drop.confidence == "high":
            keep.confidence = "high"
        best[key] = keep
    return list(best.values())
