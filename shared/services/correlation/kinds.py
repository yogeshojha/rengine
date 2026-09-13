"""Where each correlation kind's value is read from, and what marks one as a provider's."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, cast, func
from sqlalchemy.dialects.postgresql import JSONB

from shared.definitions.correlation import MIN_BODY_BYTES, CorrelationKind
from shared.models.http_asset import HttpAsset
from shared.models.subdomain import Subdomain
from shared.utils.imagehash import hex_digest
from shared.utils.infra import public_ca, shared_edge


@dataclass(frozen=True)
class KindSpec:
    """One shared identity: the column it lives in and the shape of its value."""

    kind: str
    operator: str
    attr: str
    asset: bool = False
    json_array: bool = False
    derived: bool = False
    drop_cdn: bool = False
    numeric: bool = False
    # appended to the drill-down token
    narrows: str = ""

    @property
    def model(self) -> Any:
        return HttpAsset if self.asset else Subdomain

    @property
    def column(self) -> Any:
        return getattr(self.model, self.attr)

    def value(self) -> Any:
        """The scalar a row contributes, one per element for a list column."""
        if self.json_array:
            return func.jsonb_array_elements_text(
                cast(self.column, JSONB)
            ).column_valued(f"{self.attr}_value")
        return self.column

    def bind(self, value: str) -> Any:
        return int(value) if self.numeric else value

    def conditions(self) -> list[Any]:
        out: list[Any] = []
        if self.drop_cdn:
            out.append(Subdomain.is_cdn.is_(False))
        if self.kind == CorrelationKind.BODY.value:
            out.append(func.coalesce(HttpAsset.content_length, 0) >= MIN_BODY_BYTES)
        return out


KINDS: dict[str, KindSpec] = {
    spec.kind: spec
    for spec in (
        KindSpec(CorrelationKind.IP.value, ":", "resolved_ips", json_array=True),
        KindSpec(CorrelationKind.CNAME.value, "=", "cname"),
        KindSpec(CorrelationKind.TITLE.value, "=", "page_title"),
        KindSpec(CorrelationKind.FAVICON.value, "=", "favicon_hash"),
        KindSpec(CorrelationKind.BODY.value, "=", "content_hash", asset=True),
        KindSpec(
            CorrelationKind.SCREENSHOT.value, ":", "screenshot_phash", derived=True
        ),
        KindSpec(CorrelationKind.JARM.value, "=", "jarm", asset=True),
        KindSpec(CorrelationKind.CERT.value, "=", "tls_fingerprint", asset=True),
        KindSpec(CorrelationKind.CERT_ISSUER.value, "=", "tls_issuer", asset=True),
        KindSpec(CorrelationKind.HEADERS.value, "=", "header_hash", asset=True),
        KindSpec(CorrelationKind.TECH.value, "=", "tech", json_array=True),
        KindSpec(CorrelationKind.SERVER.value, "=", "webserver"),
        KindSpec(CorrelationKind.CDN.value, "=", "cdn_name"),
        KindSpec(
            CorrelationKind.ASN.value,
            ":",
            "asn",
            drop_cdn=True,
            numeric=True,
            narrows=" -is:cdn",
        ),
    )
}


def asset_join() -> Any:
    return and_(
        HttpAsset.scan_id == Subdomain.scan_id, HttpAsset.host == Subdomain.name
    )


def platform_for(kind: str, value: str, cdn_addresses: dict[str, str]) -> str:
    """The provider whose tenants all carry this value."""
    if kind == CorrelationKind.IP.value:
        return cdn_addresses.get(value, "")
    if kind == CorrelationKind.CNAME.value:
        return shared_edge(value) or ""
    if kind == CorrelationKind.CERT_ISSUER.value:
        return public_ca(value) or ""
    if kind == CorrelationKind.CDN.value:
        return value
    return ""


def values_carried(rows: Sequence[Any], assets: Sequence[Any]) -> dict[str, set[str]]:
    """Every correlation value a host presents, read off its row and its HTTP asset."""
    out: dict[str, set[str]] = {}
    for kind, spec in KINDS.items():
        found: set[str] = set()
        for row in assets if spec.asset else rows:
            raw = getattr(row, spec.attr, None)
            if spec.derived:
                if raw is not None:
                    found.add(hex_digest(int(raw)))
            elif spec.json_array:
                found.update(str(v) for v in (raw or []) if v not in (None, ""))
            elif raw not in (None, ""):
                found.add(str(raw))
        if found:
            out[kind] = found
    return out
