"""The stored responses a scan holds, one corpus per table."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from sqlalchemy import Select, func, or_, select

from shared.definitions.secrets import BODY_CAP_BYTES, MinerSource, SecretSource
from shared.definitions.vulnerabilities import MAX_EVIDENCE_BYTES
from shared.models.endpoint import Endpoint, EndpointResponse
from shared.models.http_asset import HttpAsset
from shared.models.vulnerability import Vulnerability


@dataclass(frozen=True)
class Document:
    asset_id: uuid.UUID | None
    host: str
    url: str
    source: str
    text: str
    truncated: bool = False


@dataclass(frozen=True)
class Corpus:
    source: str
    count: Callable[[uuid.UUID], Select]
    ids: Callable[[uuid.UUID], Select]
    rows: Callable[[Sequence[uuid.UUID]], Select]
    documents: Callable[[object], list[Document]]


def _web_asset_text():
    return or_(
        HttpAsset.response_body.isnot(None), HttpAsset.raw_response_header.isnot(None)
    )


def _web_asset_documents(row) -> list[Document]:
    out: list[Document] = []
    if row.response_body:
        out.append(
            Document(
                row.id,
                row.host,
                row.url,
                SecretSource.BODY.value,
                row.response_body,
                truncated=len(row.response_body) >= BODY_CAP_BYTES,
            )
        )
    if row.raw_response_header:
        out.append(
            Document(
                row.id,
                row.host,
                row.url,
                SecretSource.HEADER.value,
                row.raw_response_header,
            )
        )
    return out


WEB_ASSETS = Corpus(
    source=MinerSource.WEB_ASSET_RESPONSES.value,
    count=lambda scan_id: select(func.count()).where(
        HttpAsset.scan_id == scan_id, _web_asset_text()
    ),
    ids=lambda scan_id: (
        select(HttpAsset.id)
        .where(HttpAsset.scan_id == scan_id, _web_asset_text())
        .order_by(HttpAsset.host, HttpAsset.url)
    ),
    rows=lambda ids: select(
        HttpAsset.id,
        HttpAsset.host,
        HttpAsset.url,
        HttpAsset.response_body,
        HttpAsset.raw_response_header,
    ).where(HttpAsset.id.in_(ids)),
    documents=_web_asset_documents,
)


def _endpoint_documents(row) -> list[Document]:
    out: list[Document] = []
    if row.response_body:
        out.append(
            Document(
                row.http_asset_id,
                row.host,
                row.url,
                SecretSource.ENDPOINT_BODY.value,
                row.response_body,
                truncated=len(row.response_body) >= BODY_CAP_BYTES,
            )
        )
    if row.raw_response_header:
        out.append(
            Document(
                row.http_asset_id,
                row.host,
                row.url,
                SecretSource.ENDPOINT_HEADER.value,
                row.raw_response_header,
            )
        )
    return out


ENDPOINTS = Corpus(
    source=MinerSource.ENDPOINT_RESPONSES.value,
    count=lambda scan_id: select(func.count()).where(
        EndpointResponse.scan_id == scan_id
    ),
    ids=lambda scan_id: (
        select(EndpointResponse.endpoint_id)
        .join(Endpoint, Endpoint.id == EndpointResponse.endpoint_id)
        .where(EndpointResponse.scan_id == scan_id)
        .order_by(Endpoint.host, Endpoint.url)
    ),
    rows=lambda ids: (
        select(
            Endpoint.id,
            Endpoint.host,
            Endpoint.url,
            Endpoint.http_asset_id,
            EndpointResponse.response_body,
            EndpointResponse.raw_response_header,
        )
        .join(EndpointResponse, EndpointResponse.endpoint_id == Endpoint.id)
        .where(Endpoint.id.in_(ids))
    ),
    documents=_endpoint_documents,
)


def _finding_documents(row) -> list[Document]:
    if not row.response:
        return []
    url = row.url or row.matched_at
    host = row.host or (urlsplit(url).hostname or "")
    if not host:
        return []
    return [
        Document(
            row.http_asset_id,
            host,
            url,
            SecretSource.FINDING.value,
            row.response,
            truncated=len(row.response) >= MAX_EVIDENCE_BYTES,
        )
    ]


FINDINGS = Corpus(
    source=MinerSource.FINDING_RESPONSES.value,
    count=lambda scan_id: select(func.count()).where(
        Vulnerability.scan_id == scan_id, Vulnerability.response.isnot(None)
    ),
    ids=lambda scan_id: (
        select(Vulnerability.id)
        .where(Vulnerability.scan_id == scan_id, Vulnerability.response.isnot(None))
        .order_by(Vulnerability.host, Vulnerability.matched_at)
    ),
    rows=lambda ids: select(
        Vulnerability.id,
        Vulnerability.host,
        Vulnerability.url,
        Vulnerability.matched_at,
        Vulnerability.http_asset_id,
        Vulnerability.response,
    ).where(Vulnerability.id.in_(ids)),
    documents=_finding_documents,
)

CORPORA: dict[str, Corpus] = {c.source: c for c in (WEB_ASSETS, ENDPOINTS, FINDINGS)}


def corpora_for(sources: Sequence[str]) -> list[Corpus]:
    return [CORPORA[source] for source in sources]
