from __future__ import annotations

from uuid import UUID

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scan_surface import ScanSurfaceService
from shared.models.http_asset import (
    HttpAsset,
    HttpAssetDetail,
    HttpAssetRead,
    HttpAssetSummary,
    HygieneVerdict,
)
from shared.models.scan_surface import AssetSurface
from shared.services import web_hygiene


class HttpAssetService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_read(self, asset: HttpAsset) -> HttpAssetRead:
        return HttpAssetRead(
            id=asset.id,
            scan_id=asset.scan_id,
            target_id=asset.target_id,
            url=asset.url,
            final_url=asset.final_url,
            host=asset.host,
            port=asset.port,
            scheme=asset.scheme,
            method=asset.method,
            path=asset.path,
            status_code=asset.status_code,
            chain_status_codes=list(asset.chain_status_codes or []),
            title=asset.title,
            webserver=asset.webserver,
            content_type=asset.content_type,
            content_length=asset.content_length,
            location=asset.location,
            response_time=asset.response_time,
            words=asset.words,
            lines=asset.lines,
            tech=list(asset.tech or []),
            cpe=list(asset.cpe or []),
            favicon_hash=asset.favicon_hash,
            content_hash=asset.content_hash,
            header_hash=asset.header_hash,
            jarm=asset.jarm,
            supports_http2=asset.supports_http2,
            supports_pipeline=asset.supports_pipeline,
            ip=asset.ip,
            a_records=list(asset.a_records or []),
            aaaa_records=list(asset.aaaa_records or []),
            cname=asset.cname,
            asn=asset.asn,
            asn_org=asset.asn_org,
            is_cdn=asset.is_cdn,
            cdn_name=asset.cdn_name,
            cdn_type=asset.cdn_type,
            waf=asset.waf,
            tls_version=asset.tls_version,
            tls_cipher=asset.tls_cipher,
            tls_subject_cn=asset.tls_subject_cn,
            tls_sans=list(asset.tls_sans or []),
            tls_issuer=asset.tls_issuer,
            tls_issuer_org=asset.tls_issuer_org,
            tls_serial=asset.tls_serial,
            tls_fingerprint=asset.tls_fingerprint,
            tls_not_before=asset.tls_not_before,
            tls_not_after=asset.tls_not_after,
            tls_expired=asset.tls_expired,
            tls_self_signed=asset.tls_self_signed,
            screenshot_path=asset.screenshot_path,
            body_preview=asset.body_preview,
            hygiene_issues=list(asset.hygiene_issues or []),
            hygiene_checked=list(asset.hygiene_checked or []),
            discovered_at=asset.discovered_at,
        )

    def _to_detail(
        self, asset: HttpAsset, surface: AssetSurface | None = None
    ) -> HttpAssetDetail:
        verdicts = web_hygiene.evaluate_asset(asset).verdicts
        return HttpAssetDetail(
            surface=surface,
            **self._to_read(asset).model_dump(),
            tls_subject_dn=asset.tls_subject_dn,
            tls_issuer_cn=asset.tls_issuer_cn,
            raw_request=asset.raw_request,
            raw_response_header=asset.raw_response_header,
            response_body=asset.response_body,
            response_headers=dict(asset.response_headers or {}),
            hygiene=[
                HygieneVerdict(key=str(v.key), failed=v.failed, evidence=v.evidence)
                for v in verdicts
            ],
        )

    async def get(self, asset_id: UUID, project_id: UUID) -> HttpAssetDetail | None:
        query = select(HttpAsset).where(
            HttpAsset.id == asset_id, HttpAsset.project_id == project_id
        )
        result = await self.session.execute(query)
        asset = result.scalar_one_or_none()
        if asset is None:
            return None
        surface = await ScanSurfaceService(self.session).for_asset(
            asset.scan_id, asset.id
        )
        return self._to_detail(asset, surface)

    def _filters(
        self,
        project_id: UUID,
        scan_id: UUID | None,
        target_id: UUID | None,
        search: str | None,
    ) -> list:
        conditions = [HttpAsset.project_id == project_id]
        if scan_id is not None:
            conditions.append(HttpAsset.scan_id == scan_id)
        if target_id is not None:
            conditions.append(HttpAsset.target_id == target_id)
        if search:
            conditions.append(HttpAsset.url.ilike(f"%{search}%"))
        return conditions

    def _base_query(
        self,
        project_id: UUID,
        scan_id: UUID | None,
        target_id: UUID | None,
        search: str | None,
    ):
        return select(HttpAsset).where(
            *self._filters(project_id, scan_id, target_id, search)
        )

    async def list(
        self,
        project_id: UUID,
        scan_id: UUID | None = None,
        target_id: UUID | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[HttpAssetRead]:
        query = self._base_query(project_id, scan_id, target_id, search)
        query = (
            query.order_by(HttpAsset.host, HttpAsset.port).limit(limit).offset(offset)
        )
        result = await self.session.execute(query)
        return [self._to_read(a) for a in result.scalars().all()]

    async def summary(
        self,
        project_id: UUID,
        scan_id: UUID | None = None,
        target_id: UUID | None = None,
    ) -> HttpAssetSummary:
        where = self._filters(project_id, scan_id, target_id, None)
        totals = (
            await self.session.execute(
                select(
                    func.count(),
                    func.count().filter(HttpAsset.is_cdn.is_(True)),
                ).where(*where)
            )
        ).one()
        status_rows = (
            await self.session.execute(
                select(HttpAsset.status_code, func.count())
                .where(*where, HttpAsset.status_code.isnot(None))
                .group_by(HttpAsset.status_code)
            )
        ).all()
        tech = func.jsonb_array_elements_text(
            cast(HttpAsset.tech, JSONB)
        ).column_valued("v")
        tech_rows = (
            await self.session.execute(
                select(tech, func.count())
                .select_from(HttpAsset)
                .where(*where)
                .group_by(tech)
            )
        ).all()
        return HttpAssetSummary(
            total=int(totals[0] or 0),
            by_status={str(code): int(n) for code, n in status_rows},
            by_tech={str(name): int(n) for name, n in tech_rows},
            cdn=int(totals[1] or 0),
        )
