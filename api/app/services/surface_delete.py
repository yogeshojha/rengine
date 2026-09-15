"""Removing result rows: what each dimension addresses, and what cannot stand without it."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, status
from sqlalchemy import Uuid, delete, select, tuple_

from shared.definitions.surface import SurfaceDimension
from shared.models.endpoint import Endpoint
from shared.models.http_asset import HttpAsset
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.secret import Secret
from shared.models.software import SoftwareCve
from shared.models.subdomain import Subdomain
from shared.models.surface import SurfaceDeleteResult
from shared.models.vulnerability import Vulnerability
from shared.services.asset_query import lead_cache

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.asset_query import QueryScope


@dataclass(frozen=True)
class DeleteSpec:
    """One dimension's table and the columns a table may address its rows by."""

    model: Any
    keys: tuple[str, ...]


SPECS: dict[str, DeleteSpec] = {
    SurfaceDimension.WEB_ASSETS.value: DeleteSpec(Subdomain, ("id", "name")),
    SurfaceDimension.ENDPOINTS.value: DeleteSpec(Endpoint, ("id", "signature")),
    SurfaceDimension.SERVICES.value: DeleteSpec(Port, ("id",)),
    SurfaceDimension.IPS.value: DeleteSpec(IpAddress, ("ip",)),
    SurfaceDimension.VULNERABILITIES.value: DeleteSpec(
        Vulnerability, ("id", "fingerprint", "template_id")
    ),
    SurfaceDimension.SOFTWARE.value: DeleteSpec(SoftwareCve, ("id", "fingerprint")),
    SurfaceDimension.SECRETS.value: DeleteSpec(Secret, ("id", "fingerprint")),
}


def _spec(dimension: str) -> DeleteSpec:
    spec = SPECS.get(dimension)
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown dimension '{dimension}'.",
        )
    return spec


def _column(spec: DeleteSpec, key: str | None):
    name = key or spec.keys[0]
    if name not in spec.keys:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Rows cannot be addressed by '{name}'. Expected one of "
            f"{', '.join(spec.keys)}.",
        )
    return getattr(spec.model, name)


def _values(column, ids: list[str]) -> list[Any]:
    if not isinstance(column.type, Uuid):
        return ids
    parsed: list[uuid.UUID] = []
    for value in ids:
        try:
            parsed.append(uuid.UUID(value))
        except ValueError:
            continue
    return parsed


class SurfaceDeleteService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def delete(
        self,
        scope: QueryScope,
        dimension: str,
        ids: list[str],
        key: str | None = None,
    ) -> SurfaceDeleteResult:
        spec = _spec(dimension)
        column = _column(spec, key)
        values = _values(column, ids)
        result = SurfaceDeleteResult(dimension=dimension)
        if not values:
            return result

        model = spec.model
        where = (scope.match(model.scan_id), column.in_(values))
        web_assets = dimension == SurfaceDimension.WEB_ASSETS.value
        named = (model.name,) if web_assets else ()
        doomed = (
            await self.session.execute(
                select(model.scan_id, model.target_id, *named).where(*where).distinct()
            )
        ).all()
        if not doomed:
            return result

        removed = await self.session.execute(delete(model).where(*where))
        result.deleted = removed.rowcount or 0
        if web_assets:
            result.related = await self._responses(doomed)
        await self.session.commit()
        await lead_cache.bump({row.target_id for row in doomed})
        return result

    async def _responses(self, doomed) -> dict[str, int]:
        pairs = {(row.scan_id, row.name) for row in doomed}
        removed = await self.session.execute(
            delete(HttpAsset).where(
                tuple_(HttpAsset.scan_id, HttpAsset.host).in_(pairs)
            )
        )
        count = removed.rowcount or 0
        return {"http_assets": count} if count else {}
