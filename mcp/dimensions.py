"""The five result dimensions, adapted for tools.

One entry per dimension. Add a sixth here and `query_assets`, `group_assets`,
`surface_brief` and `describe_query_language` all cover it with no further edits.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from shared.definitions.asset_query import (
    ENDPOINT_QUERY,
    HOST_QUERY,
    IP_QUERY,
    SERVICE_QUERY,
    VULN_QUERY,
    QueryRegistry,
)
from shared.definitions.surface import (
    SURFACE_LABELS,
    SURFACE_NOUN,
    SURFACE_ORDER,
    SurfaceDimension,
)

if TYPE_CHECKING:
    from pydantic import BaseModel
    from sqlalchemy.ext.asyncio import AsyncSession

MAX_ROWS = 40
DEFAULT_ROWS = 20


@dataclass(frozen=True)
class Dimension:
    key: str
    registry: QueryRegistry
    # the scan-page tab a pivot link opens
    tab: str
    filter_path: str
    service_path: str
    # fields kept from a row; a raw row costs ~205 tokens, these cost ~25
    fields: tuple[str, ...]
    # the column a human reads first
    identity: str
    needs_project: bool = False
    page_args: tuple[str, str] = ("limit", "offset")
    order_arg: str = "order"

    @property
    def label(self) -> str:
        return SURFACE_LABELS[self.key]

    @property
    def noun(self) -> str:
        return SURFACE_NOUN[self.key][0]

    @property
    def noun_plural(self) -> str:
        return SURFACE_NOUN[self.key][1]

    def load_filter(self) -> type[BaseModel]:
        return _load(self.filter_path)

    def service(self, session: AsyncSession) -> Any:
        return _load(self.service_path)(session)

    def build_filter(
        self, query: str | None, limit: int, offset: int, **extra: Any
    ) -> BaseModel:
        size_arg, offset_arg = self.page_args
        payload: dict[str, Any] = {"q": query or None, size_arg: limit}
        payload[offset_arg] = offset if offset_arg == "offset" else max(1, offset)
        payload.update({k: v for k, v in extra.items() if v is not None})
        return self.load_filter().model_validate(payload)

    def compact(self, row: Any) -> dict:
        data = row if isinstance(row, dict) else row.model_dump(mode="json")
        return {
            k: data[k] for k in self.fields if data.get(k) not in (None, [], {}, "")
        }

    async def search(
        self, session: AsyncSession, scan_id: uuid.UUID, f: Any, project_id: uuid.UUID
    ) -> Any:
        service = self.service(session)
        if self.needs_project:
            return await service.search(project_id=project_id, scan_id=scan_id, f=f)
        return await service.search(scan_id, f)

    async def leads(
        self, session: AsyncSession, scan_id: uuid.UUID, f: Any, project_id: uuid.UUID
    ) -> Any:
        service = self.service(session)
        if self.needs_project:
            return await service.leads(project_id=project_id, scan_id=scan_id, f=f)
        return await service.leads(scan_id, f)

    async def groups(
        self,
        session: AsyncSession,
        scan_id: uuid.UUID,
        f: Any,
        key: str,
        project_id: uuid.UUID,
    ) -> Any:
        service = self.service(session)
        if self.needs_project:
            return await service.groups(
                project_id=project_id, scan_id=scan_id, f=f, key=key
            )
        return await service.groups(scan_id, f, key)


def _load(path: str) -> Any:
    module_name, _, attribute = path.rpartition(".")
    import importlib  # noqa: PLC0415

    return getattr(importlib.import_module(module_name), attribute)


DIMENSIONS: tuple[Dimension, ...] = (
    Dimension(
        key=SurfaceDimension.WEB_ASSETS.value,
        registry=HOST_QUERY,
        tab="web-assets",
        filter_path="shared.models.subdomain.SubdomainFilter",
        service_path="app.services.subdomain.SubdomainService",
        fields=(
            "name",
            "http_status",
            "page_title",
            "http_url",
            "tech",
            "webserver",
            "resolved_ips",
            "cname",
            "is_cdn",
            "cdn_name",
            "waf",
            "asn_org",
            "ports",
            "tls_expired",
            "endpoint_count",
            "vuln_count",
            "vuln_severity",
            "vuln_kev",
        ),
        identity="name",
        needs_project=True,
    ),
    Dimension(
        key=SurfaceDimension.IPS.value,
        registry=IP_QUERY,
        tab="ips",
        filter_path="shared.models.scan_correlation.IpGroupFilter",
        service_path="app.services.ip_address.IpAddressService",
        fields=(
            "ip",
            "version",
            "asn",
            "asn_org",
            "country",
            "prefix",
            "is_cdn",
            "cdn_name",
            "is_alive",
            "ports",
            "port_count",
            "host_count",
            "hosts",
            "has_sensitive",
        ),
        identity="ip",
    ),
    Dimension(
        key=SurfaceDimension.SERVICES.value,
        registry=SERVICE_QUERY,
        tab="services",
        filter_path="shared.models.scan_correlation.ServiceFilter",
        service_path="app.services.port.PortService",
        fields=(
            "ip",
            "port",
            "protocol",
            "service_name",
            "service_class",
            "product",
            "version",
            "is_http",
            "tls",
            "status_code",
            "title",
            "url",
            "hosts",
            "asn_org",
            "country",
            "is_cdn",
            "is_sensitive",
            "source",
            "is_new",
        ),
        identity="ip",
    ),
    Dimension(
        key=SurfaceDimension.VULNERABILITIES.value,
        registry=VULN_QUERY,
        tab="vulnerabilities",
        filter_path="shared.models.vulnerability.VulnerabilityFilter",
        service_path="app.services.vulnerability.VulnerabilityService",
        fields=(
            "fingerprint",
            "template_id",
            "template_name",
            "severity",
            "scanner",
            "matched_at",
            "host",
            "ip",
            "port",
            "cve_ids",
            "cvss_score",
            "epss_score",
            "is_kev",
            "state",
            "is_new",
            "tags",
        ),
        identity="template_name",
    ),
    Dimension(
        key=SurfaceDimension.ENDPOINTS.value,
        registry=ENDPOINT_QUERY,
        tab="endpoints",
        filter_path="shared.models.endpoint.EndpointFilter",
        service_path="app.services.endpoint.EndpointService",
        fields=(
            "url",
            "host",
            "path",
            "status_code",
            "content_type",
            "content_length",
            "title",
            "methods",
            "param_count",
            "endpoint_class",
            "interest",
            "primary_source",
            "is_probed",
            "is_new",
        ),
        identity="url",
        page_args=("size", "page"),
        order_arg="direction",
    ),
)


@lru_cache(maxsize=1)
def by_key() -> dict[str, Dimension]:
    return {d.key: d for d in DIMENSIONS}


def dimension(key: str) -> Dimension:
    found = by_key().get(key)
    if found is None:
        from mcp.errors import InvalidParamsError  # noqa: PLC0415

        known = ", ".join(DIMENSION_KEYS)
        msg = f"Unknown dimension {key!r}. Use one of: {known}."
        raise InvalidParamsError(msg)
    return found


DIMENSION_KEYS: tuple[str, ...] = tuple(
    key for key in SURFACE_ORDER if key in {d.key for d in DIMENSIONS}
)

DimensionResolver = Callable[[str], Dimension]
