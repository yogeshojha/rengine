"""The five result dimensions, adapted for tools."""

from __future__ import annotations

import uuid
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
    SURFACE_COLUMNS,
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
    needs_project: bool = False
    page_args: tuple[str, str] = ("limit", "offset")

    @property
    def fields(self) -> tuple[str, ...]:
        return SURFACE_COLUMNS[self.key]

    @property
    def label(self) -> str:
        return SURFACE_LABELS[self.key]

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
        payload[offset_arg] = (
            offset if offset_arg == "offset" else offset // max(1, limit) + 1
        )
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
        needs_project=True,
    ),
    Dimension(
        key=SurfaceDimension.IPS.value,
        registry=IP_QUERY,
        tab="ips",
        filter_path="shared.models.scan_correlation.IpGroupFilter",
        service_path="app.services.ip_address.IpAddressService",
    ),
    Dimension(
        key=SurfaceDimension.SERVICES.value,
        registry=SERVICE_QUERY,
        tab="services",
        filter_path="shared.models.scan_correlation.ServiceFilter",
        service_path="app.services.port.PortService",
    ),
    Dimension(
        key=SurfaceDimension.VULNERABILITIES.value,
        registry=VULN_QUERY,
        tab="vulnerabilities",
        filter_path="shared.models.vulnerability.VulnerabilityFilter",
        service_path="app.services.vulnerability.VulnerabilityService",
    ),
    Dimension(
        key=SurfaceDimension.ENDPOINTS.value,
        registry=ENDPOINT_QUERY,
        tab="endpoints",
        filter_path="shared.models.endpoint.EndpointFilter",
        service_path="app.services.endpoint.EndpointService",
        page_args=("size", "page"),
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
