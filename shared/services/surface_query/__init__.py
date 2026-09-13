"""One definition of each dimension's filtered set, for the api and the worker alike."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from shared.definitions.surface import SurfaceDimension
from shared.services.surface_query import (
    endpoints,
    ips,
    services,
    vulnerabilities,
    web_assets,
)

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from pydantic import BaseModel
    from sqlalchemy import Select

    from shared.services.asset_query import QueryScope


@dataclass(frozen=True)
class Built:
    """A filtered statement and the source its columns hang off."""

    statement: Select
    source: Any


@dataclass(frozen=True)
class SurfaceQuery:
    dimension: str
    module: Any
    filter_path: str
    needs_project: bool = False
    takes_source: bool = False
    order_needs_scope: bool = False

    @property
    def filter_model(self) -> type[BaseModel]:
        module_name, _, attribute = self.filter_path.rpartition(".")
        import importlib  # noqa: PLC0415

        return getattr(importlib.import_module(module_name), attribute)

    def build(
        self,
        scope: QueryScope,
        f: BaseModel,
        now: datetime,
        *,
        project_id: UUID | None = None,
        columns=None,
    ) -> Built:
        if self.needs_project:
            return Built(
                self.module.scoped(project_id, scope, f, now, columns=columns), None
            )
        if self.takes_source:
            source, statement = self.module.scoped(scope, f, columns=columns)
            return Built(statement, source)
        return Built(self.module.scoped(scope, f, columns=columns), None)

    def order(self, built: Built, f: BaseModel, scope: QueryScope) -> Select:
        if self.takes_source:
            return self.module.order(built.statement, built.source, f)
        if self.order_needs_scope:
            return self.module.order(built.statement, f, scope)
        return self.module.order(built.statement, f)

    def compiled(self, built: Built, scope: QueryScope, f: BaseModel, now: datetime):
        """The query language predicate, or None when the query is empty."""
        if self.takes_source:
            return self.module.compiled(scope, f, now, built.source)
        return self.module.compiled(scope, f, now)

    def filtered(
        self,
        scope: QueryScope,
        f: BaseModel,
        now: datetime,
        *,
        project_id: UUID | None = None,
        columns=None,
    ) -> Built:
        """The statement the table shows: scope, facets and the typed query."""
        built = self.build(scope, f, now, project_id=project_id, columns=columns)
        predicate = self.compiled(built, scope, f, now)
        if predicate is None:
            return built
        return Built(built.statement.where(predicate), built.source)


QUERIES: tuple[SurfaceQuery, ...] = (
    SurfaceQuery(
        SurfaceDimension.WEB_ASSETS.value,
        web_assets,
        "shared.models.subdomain.SubdomainFilter",
        needs_project=True,
    ),
    SurfaceQuery(
        SurfaceDimension.ENDPOINTS.value,
        endpoints,
        "shared.models.endpoint.EndpointFilter",
    ),
    SurfaceQuery(
        SurfaceDimension.SERVICES.value,
        services,
        "shared.models.scan_correlation.ServiceFilter",
        takes_source=True,
    ),
    SurfaceQuery(
        SurfaceDimension.IPS.value,
        ips,
        "shared.models.scan_correlation.IpGroupFilter",
        takes_source=True,
    ),
    SurfaceQuery(
        SurfaceDimension.VULNERABILITIES.value,
        vulnerabilities,
        "shared.models.vulnerability.VulnerabilityFilter",
        order_needs_scope=True,
    ),
)


@lru_cache(maxsize=1)
def by_dimension() -> dict[str, SurfaceQuery]:
    return {q.dimension: q for q in QUERIES}


def for_dimension(dimension: str) -> SurfaceQuery:
    query = by_dimension().get(dimension)
    if query is None:
        msg = f"unknown dimension {dimension!r}"
        raise KeyError(msg)
    return query


__all__ = [
    "QUERIES",
    "Built",
    "SurfaceQuery",
    "by_dimension",
    "endpoints",
    "for_dimension",
    "ips",
    "services",
    "vulnerabilities",
    "web_assets",
]
