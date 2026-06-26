from __future__ import annotations

from collections import Counter
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.http_asset import (
    HttpAsset,
    HttpAssetDetail,
    HttpAssetRead,
    HttpAssetSummary,
)


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
            discovered_at=asset.discovered_at,
        )

    def _to_detail(self, asset: HttpAsset) -> HttpAssetDetail:
        return HttpAssetDetail(
            **self._to_read(asset).model_dump(),
            tls_subject_dn=asset.tls_subject_dn,
            tls_issuer_cn=asset.tls_issuer_cn,
            raw_request=asset.raw_request,
            raw_response_header=asset.raw_response_header,
            response_body=asset.response_body,
            response_headers=dict(asset.response_headers or {}),
        )

    async def get(self, asset_id: UUID, project_id: UUID) -> HttpAssetDetail | None:
        query = select(HttpAsset).where(
            HttpAsset.id == asset_id, HttpAsset.project_id == project_id
        )
        result = await self.session.execute(query)
        asset = result.scalar_one_or_none()
        return self._to_detail(asset) if asset else None

    def _base_query(
        self,
        project_id: UUID,
        scan_id: UUID | None,
        target_id: UUID | None,
        search: str | None,
    ):
        query = select(HttpAsset).where(HttpAsset.project_id == project_id)
        if scan_id is not None:
            query = query.where(HttpAsset.scan_id == scan_id)
        if target_id is not None:
            query = query.where(HttpAsset.target_id == target_id)
        if search:
            query = query.where(HttpAsset.url.ilike(f"%{search}%"))
        return query

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
        query = self._base_query(project_id, scan_id, target_id, None)
        result = await self.session.execute(query)
        rows = result.scalars().all()
        by_status: Counter = Counter()
        by_tech: Counter = Counter()
        cdn = 0
        for row in rows:
            if row.status_code is not None:
                by_status[str(row.status_code)] += 1
            if row.is_cdn:
                cdn += 1
            for tech in row.tech or []:
                by_tech[tech] += 1
        return HttpAssetSummary(
            total=len(rows),
            by_status=dict(by_status),
            by_tech=dict(by_tech),
            cdn=cdn,
        )

    async def count(
        self,
        project_id: UUID,
        scan_id: UUID | None = None,
        target_id: UUID | None = None,
    ) -> int:
        query = select(func.count()).select_from(
            self._base_query(project_id, scan_id, target_id, None).subquery()
        )
        result = await self.session.execute(query)
        return int(result.scalar_one())
