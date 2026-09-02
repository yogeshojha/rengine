import csv
import io
from collections import Counter
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import Select, func, select
from sqlalchemy import delete as sa_delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.services.target_filters import (
    SignalName,
    SortDir,
    SortKey,
    apply_filters,
    apply_sort,
    signal_count_columns,
    with_whois_join,
)
from shared.enums.activity import ActivityLevel
from shared.enums.scan import SCAN_LIVE_STATUSES
from shared.enums.target import TargetType
from shared.enums.task_status import TaskStatus
from shared.models import (
    Organization,
    OrganizationSummary,
    Project,
    Tag,
    TagSummary,
    Target,
    TargetBulkCreate,
    TargetBulkCreateResponse,
    TargetCreate,
    TargetImportItem,
    TargetImportRequest,
    TargetImportResult,
    TargetRead,
    TargetUpdate,
)
from shared.models.activity_log import ActivityEvent
from shared.models.bgp_summary import BgpSummaryRead, TargetBgpSummary
from shared.models.dns import DnsLookup, DnsLookupRead, DnsRecordRead
from shared.models.ripestat import (
    RIPEStatAbuseContact,
    RIPEStatAnnouncedPrefix,
    RIPEStatASNNeighbour,
    RIPEStatASOverview,
    RIPEStatNetworkInfo,
    RIPEStatPrefixOverview,
    RIPEStatRelatedPrefix,
)
from shared.models.scan import Scan
from shared.models.whois import WhoisRecordRead, WhoisRecordSummary
from shared.schemas.target_detail import (
    AbuseContactDetail,
    AnnouncedPrefixDetail,
    ASNNeighbourDetail,
    ASOverviewDetail,
    EnrichmentRefreshResponse,
    NetworkInfoDetail,
    PrefixOverviewDetail,
    RelatedPrefixDetail,
    TargetBgpDetailResponse,
    TargetDetailRead,
    TargetDnsDetailResponse,
    TargetWhoisDetailResponse,
)
from shared.services import get_or_create_organization, get_or_create_tag
from shared.services.activity_log import ActivityLogService
from shared.services.celery_dispatch import (
    dispatch_dns_lookups,
    dispatch_ripestat_enrichment,
    dispatch_whois_lookups,
)
from shared.utils.datetime import utc_now
from shared.utils.validation import validate_target
from tools.dnsx.service import DnsxService

MAX_TARGETS_IMPORT = 500

BGP_ELIGIBLE_TYPES = {TargetType.IP, TargetType.IP_RANGE, TargetType.ASN}
DNS_ELIGIBLE_TYPES = {TargetType.DOMAIN, TargetType.URL}


@dataclass
class BulkTargetResult:
    import_result: TargetImportResult
    target: Target | None = None


class TargetService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._activity = ActivityLogService(session)

    async def validate_target_value(self, target_value: str) -> TargetType | None:
        return validate_target(target_value)

    async def get_target_counts(self, project_slug: str) -> dict[str, int]:
        project = await self._get_project_by_slug(project_slug)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        result = await self.session.execute(
            select(Target.target_type, func.count(Target.id))
            .where(Target.project_id == project.id)
            .group_by(Target.target_type)
        )

        counts = {
            "all": 0,
            "domain": 0,
            "ip": 0,
            "ip_range": 0,
            "asn": 0,
            "url": 0,
        }

        for target_type, count in result.all():
            counts[target_type.value] = count
            counts["all"] += count

        return counts

    async def search_targets_by_value(
        self,
        target_value: str,
        project_slug: str | None = None,
    ) -> select:
        query = select(Target).where(Target.target_value.ilike(f"%{target_value}%"))

        if project_slug:
            project = await self._get_project_by_slug(project_slug)
            if not project:
                return query.where(col(Target.id).is_(None))
            query = query.where(Target.project_id == project.id)

        return query

    async def get_targets_by_value(self, target_value: str) -> list[Target]:
        result = await self.session.execute(
            select(Target).where(Target.target_value == target_value)
        )
        return list(result.scalars().all())

    async def list_targets(
        self,
        *,
        project_slug: str | None = None,
        search: str | None = None,
        organization_ids: list[UUID] | None = None,
        tag_ids: list[UUID] | None = None,
        target_type: TargetType | None = None,
        signal: SignalName | None = None,
        sort_by: SortKey = "updated",
        sort_dir: SortDir = "desc",
    ) -> Select:
        query = with_whois_join(select(Target))

        if project_slug:
            project = await self._get_project_by_slug(project_slug)
            if not project:
                return query.where(col(Target.id).is_(None))
            query = query.where(Target.project_id == project.id)

        query = apply_filters(
            query,
            search=search,
            organization_ids=organization_ids,
            tag_ids=tag_ids,
            target_type=target_type,
            signal=signal,
        )

        return apply_sort(query, sort_by, sort_dir)

    async def get_target_stats(
        self,
        *,
        project_slug: str,
        search: str | None = None,
        organization_ids: list[UUID] | None = None,
        tag_ids: list[UUID] | None = None,
        target_type: TargetType | None = None,
    ) -> dict[str, int]:
        empty = {
            "total": 0,
            "expiring": 0,
            "attention": 0,
            "awaiting": 0,
            "enriched": 0,
        }

        project = await self._get_project_by_slug(project_slug)
        if not project:
            return empty

        query = with_whois_join(
            select(*signal_count_columns()).select_from(Target)
        ).where(Target.project_id == project.id)
        query = apply_filters(
            query,
            search=search,
            organization_ids=organization_ids,
            tag_ids=tag_ids,
            target_type=target_type,
            signal=None,
        )

        row = (await self.session.execute(query)).one()
        return {
            "total": row.total,
            "expiring": row.expiring,
            "attention": row.attention,
            "awaiting": row.awaiting,
            "enriched": row.enriched,
        }

    async def get_matching_target_ids(
        self,
        *,
        project_slug: str,
        search: str | None = None,
        organization_ids: list[UUID] | None = None,
        tag_ids: list[UUID] | None = None,
        target_type: TargetType | None = None,
        signal: SignalName | None = None,
        limit: int = 10000,
    ) -> list[UUID]:
        project = await self._get_project_by_slug(project_slug)
        if not project:
            return []
        query = with_whois_join(select(Target.id)).where(
            Target.project_id == project.id
        )
        query = apply_filters(
            query,
            search=search,
            organization_ids=organization_ids,
            tag_ids=tag_ids,
            target_type=target_type,
            signal=signal,
        )
        result = await self.session.execute(query.limit(limit))
        return list(result.scalars().all())

    async def bulk_enrich(self, target_ids: list[UUID], kind: str) -> int:
        result = await self.session.execute(
            select(Target).where(Target.id.in_(target_ids))
        )
        targets = list(result.scalars().all())
        eligible: list[Target] = []

        for target in targets:
            if kind == "whois":
                target.whois_status = TaskStatus.PENDING
                target.whois_error = None
                eligible.append(target)
            elif kind == "dns" and target.target_type in DNS_ELIGIBLE_TYPES:
                target.dns_status = TaskStatus.PENDING
                target.dns_error = None
                eligible.append(target)
            elif kind == "bgp" and target.target_type in BGP_ELIGIBLE_TYPES:
                target.bgp_status = TaskStatus.PENDING
                eligible.append(target)
            else:
                continue
            target.updated_at = utc_now()

        await self.session.commit()

        ids = [str(t.id) for t in eligible]
        if ids:
            if kind == "whois":
                dispatch_whois_lookups(ids)
            elif kind == "dns":
                dispatch_dns_lookups(ids)
            else:
                dispatch_ripestat_enrichment(ids)
        return len(ids)

    async def bulk_add_tags(
        self, target_ids: list[UUID], tag_names: list[str], user_id: str
    ) -> int:
        result = await self.session.execute(
            select(Target).where(Target.id.in_(target_ids))
        )
        targets = list(result.scalars().all())
        cache: dict[tuple, Tag] = {}

        for target in targets:
            existing = {tag.id for tag in target.tags}
            for name in tag_names:
                clean = name.strip()
                if not clean:
                    continue
                key = (target.project_id, clean.lower())
                tag = cache.get(key)
                if tag is None:
                    tag = await get_or_create_tag(
                        clean, target.project_id, user_id, self.session
                    )
                    cache[key] = tag
                if tag.id not in existing:
                    target.tags.append(tag)
                    existing.add(tag.id)
            target.updated_at = utc_now()

        await self.session.commit()
        return len(targets)

    async def bulk_add_organizations(
        self, target_ids: list[UUID], org_names: list[str], user_id: str
    ) -> int:
        result = await self.session.execute(
            select(Target).where(Target.id.in_(target_ids))
        )
        targets = list(result.scalars().all())
        cache: dict[tuple, Organization] = {}

        for target in targets:
            existing = {org.id for org in target.organizations}
            for name in org_names:
                clean = name.strip()
                if not clean:
                    continue
                key = (target.project_id, clean.lower())
                org = cache.get(key)
                if org is None:
                    org = await get_or_create_organization(
                        clean, target.project_id, user_id, self.session
                    )
                    cache[key] = org
                if org.id not in existing:
                    target.organizations.append(org)
                    existing.add(org.id)
            target.updated_at = utc_now()

        await self.session.commit()
        return len(targets)

    async def create_target(self, target_in: TargetCreate, user_id: str) -> TargetRead:
        target_type = validate_target(target_in.target_value)
        if not target_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid target format",
            )

        project = await self._get_project_by_slug(target_in.project_slug)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        await self._check_duplicate_target(target_in.target_value, project.id)

        organizations = await self._get_or_create_organizations(
            target_in.organization_names, project.id, user_id
        )
        tags = await self._get_or_create_tags(target_in.tag_names, project.id, user_id)

        target = Target(
            target_value=target_in.target_value,
            target_type=target_type,
            display_name=target_in.display_name or target_in.target_value,
            project_id=project.id,
            created_by=user_id,
            organizations=organizations,
            tags=tags,
        )
        self.session.add(target)
        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Target already exists in this project",
            ) from e
        await self.session.refresh(target)

        await self._activity.log_async(
            event=ActivityEvent.TARGET_CREATED,
            title="Target created.",
            target_id=target.id,
            project_id=target.project_id,
            user_id=user_id,
        )
        await self.session.commit()

        self._dispatch_post_target_creation([target])

        return self._to_target_read(target)

    async def bulk_create_targets(
        self, bulk_in: TargetBulkCreate, user_id: str
    ) -> TargetBulkCreateResponse:
        project = await self._get_project_by_slug(bulk_in.project_slug)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        existing_targets_result = await self.session.execute(
            select(Target.target_value).where(Target.project_id == project.id)
        )
        existing_target_values = set(existing_targets_result.scalars().all())

        organizations = await self._get_or_create_organizations(
            bulk_in.organization_names, project.id, user_id
        )
        tags = await self._get_or_create_tags(bulk_in.tag_names, project.id, user_id)

        results: list[TargetImportResult] = []
        imported_count = 0
        failed_count = 0
        skipped_duplicates = 0
        seen_in_batch: set[str] = set()
        created_targets: list[Target] = []

        for target_value in bulk_in.targets:
            result = await self._process_bulk_target(
                target_value=target_value,
                project_id=project.id,
                user_id=user_id,
                organizations=organizations,
                tags=tags,
                existing_target_values=existing_target_values,
                seen_in_batch=seen_in_batch,
            )

            results.append(result.import_result)

            if result.import_result.success:
                imported_count += 1
                if result.target:
                    created_targets.append(result.target)
            elif "duplicate" in result.import_result.error.lower():
                skipped_duplicates += 1
            else:
                failed_count += 1

        await self.session.commit()

        await self._activity.log_async(
            event=ActivityEvent.TARGET_BULK_IMPORTED,
            title=f"Imported {imported_count} targets",
            description=f"{failed_count} failed, {skipped_duplicates} duplicates skipped",
            level=ActivityLevel.SUCCESS
            if imported_count > 0
            else ActivityLevel.WARNING,
            project_id=project.id,
            user_id=user_id,
        )
        await self.session.commit()

        self._dispatch_post_target_creation(created_targets)

        return TargetBulkCreateResponse(
            total=len(bulk_in.targets),
            imported=imported_count,
            failed=failed_count,
            skipped_duplicates=skipped_duplicates,
            results=results,
        )

    async def get_target(self, target_id: str) -> TargetRead:
        target = await self._get_target_or_404(target_id)
        return self._to_target_read(target)

    async def update_target(
        self, target_id: str, target_in: TargetUpdate, user_id: str
    ) -> TargetRead:
        target = await self._get_target_or_404(target_id)

        if target_in.display_name is not None:
            target.display_name = target_in.display_name

        if target_in.organization_names is not None:
            organizations = await self._get_or_create_organizations(
                target_in.organization_names, target.project_id, user_id
            )
            target.organizations = organizations

        if target_in.tag_names is not None:
            tags = await self._get_or_create_tags(
                target_in.tag_names, target.project_id, user_id
            )
            target.tags = tags

        target.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(target)

        await self._activity.log_async(
            event=ActivityEvent.TARGET_UPDATED,
            title=f"Target updated: {target.target_value}",
            target_id=target.id,
            project_id=target.project_id,
            user_id=user_id,
        )
        await self.session.commit()

        return self._to_target_read(target)

    async def delete_target(self, target_id: str, user_id: str) -> None:
        target = await self._get_target_or_404(target_id)

        # scans cascade with the target — a live one would keep probing a deleted asset
        running = (
            await self.session.execute(
                select(func.count())
                .select_from(Scan)
                .where(Scan.target_id == target.id, Scan.status.in_(SCAN_LIVE_STATUSES))
            )
        ).scalar_one()
        if running:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"'{target.target_value}' has {running} running "
                    f"scan{'s' if running != 1 else ''}. Cancel them before deleting."
                ),
            )

        target_value = target.target_value
        project_id = target.project_id

        await self.session.execute(
            sa_delete(TargetBgpSummary).where(TargetBgpSummary.target_id == target.id)
        )

        await self.session.delete(target)
        await self.session.commit()

        await self._activity.log_async(
            event=ActivityEvent.TARGET_DELETED,
            title=f"Target deleted: {target_value}",
            project_id=project_id,
            user_id=user_id,
        )
        await self.session.commit()

    async def import_targets_csv(
        self, project_slug: str, file: UploadFile, user_id: str
    ) -> TargetBulkCreateResponse:
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be a CSV file",
            )

        try:
            content = await file.read()
            csv_text = content.decode("utf-8")
        except UnicodeDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be UTF-8 encoded",
            ) from e

        targets_data = self._parse_csv_to_targets(csv_text)

        if not targets_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid targets found in CSV file",
            )

        if len(targets_data) > MAX_TARGETS_IMPORT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Too many targets in CSV file. Maximum is {MAX_TARGETS_IMPORT}, found {len(targets_data)}",
            )

        import_request = TargetImportRequest(
            project_slug=project_slug,
            targets=targets_data,
        )

        return await self.import_targets_structured(import_request, user_id)

    async def import_targets_structured(
        self, import_request: TargetImportRequest, user_id: str
    ) -> TargetBulkCreateResponse:
        project = await self._get_project_by_slug(import_request.project_slug)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        existing_targets_result = await self.session.execute(
            select(Target.target_value).where(Target.project_id == project.id)
        )
        existing_target_values = set(existing_targets_result.scalars().all())

        results: list[TargetImportResult] = []
        imported_count = 0
        failed_count = 0
        skipped_duplicates = 0
        seen_in_batch: set[str] = set()
        created_targets: list[Target] = []

        for item in import_request.targets:
            result = await self._process_import_item(
                item=item,
                project_id=project.id,
                user_id=user_id,
                existing_target_values=existing_target_values,
                seen_in_batch=seen_in_batch,
            )

            results.append(result.import_result)

            if result.import_result.success:
                imported_count += 1
                if result.target:
                    created_targets.append(result.target)
            elif "duplicate" in result.import_result.error.lower():
                skipped_duplicates += 1
            else:
                failed_count += 1

        await self.session.commit()

        total = imported_count + failed_count + skipped_duplicates
        await self._activity.log_async(
            event=ActivityEvent.TARGET_BULK_IMPORTED,
            title=f"Imported {imported_count} targets from CSV",
            description=f"{imported_count}/{total} imported successfully"
            + (f", {failed_count} failed" if failed_count else "")
            + (f", {skipped_duplicates} skipped" if skipped_duplicates else ""),
            level=ActivityLevel.SUCCESS
            if imported_count > 0
            else ActivityLevel.WARNING,
            project_id=project.id,
            user_id=user_id,
        )
        await self.session.commit()

        self._dispatch_post_target_creation(created_targets)

        return TargetBulkCreateResponse(
            total=len(import_request.targets),
            imported=imported_count,
            failed=failed_count,
            skipped_duplicates=skipped_duplicates,
            results=results,
        )

    async def get_target_detail(self, target_id: str) -> TargetDetailRead:
        target = await self._get_target_or_404(target_id)

        whois = None
        if target.whois_record:
            whois = WhoisRecordRead.model_validate(target.whois_record)

        dns = None
        if target.dns_lookup:
            dns = self._to_dns_lookup_read(target.dns_lookup)

        bgp = await self._build_bgp_detail(target)

        return TargetDetailRead(
            id=target.id,
            target_value=target.target_value,
            display_name=target.display_name,
            target_type=target.target_type,
            project_id=target.project_id,
            created_at=target.created_at,
            updated_at=target.updated_at,
            created_by=target.created_by,
            organizations=[
                OrganizationSummary(id=org.id, name=org.name, slug=org.slug)
                for org in target.organizations
            ],
            tags=[
                TagSummary(id=tag.id, name=tag.name, slug=tag.slug, color=tag.color)
                for tag in target.tags
            ],
            whois_status=target.whois_status,
            whois_error=target.whois_error,
            whois=whois,
            dns_status=target.dns_status,
            dns_error=target.dns_error,
            dns=dns,
            bgp_status=target.bgp_status,
            bgp=bgp,
        )

    async def get_target_dns(self, target_id: str) -> TargetDnsDetailResponse:
        target = await self._get_target_or_404(target_id)

        lookup = None
        if target.dns_lookup:
            lookup = self._to_dns_lookup_read(target.dns_lookup)

        return TargetDnsDetailResponse(
            target_id=target.id,
            target_type=target.target_type,
            status=target.dns_status,
            error=target.dns_error,
            lookup=lookup,
        )

    async def get_target_whois(self, target_id: str) -> TargetWhoisDetailResponse:
        target = await self._get_target_or_404(target_id)

        record = None
        if target.whois_record:
            record = WhoisRecordRead.model_validate(target.whois_record)

        return TargetWhoisDetailResponse(
            target_id=target.id,
            target_type=target.target_type,
            status=target.whois_status,
            error=target.whois_error,
            record=record,
        )

    async def get_target_bgp(self, target_id: str) -> TargetBgpDetailResponse:
        target = await self._get_target_or_404(target_id)
        return await self._build_bgp_detail(target)

    async def refresh_target_dns(self, target_id: str) -> EnrichmentRefreshResponse:
        target = await self._get_target_or_404(target_id)

        if target.target_type not in DNS_ELIGIBLE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"DNS lookup is not applicable for target type '{target.target_type.value}'. "
                f"Only domain and URL targets support DNS enrichment.",
            )

        target.dns_status = TaskStatus.PENDING
        target.dns_error = None
        target.updated_at = utc_now()
        await self.session.commit()

        await self._activity.log_async(
            event=ActivityEvent.TARGET_ENRICHMENT_STARTED,
            title=f"DNS re-enrichment queued for {target.target_value}",
            target_id=target.id,
            project_id=target.project_id,
        )
        await self.session.commit()

        dispatch_dns_lookups([str(target.id)])

        return EnrichmentRefreshResponse(
            target_id=target.id,
            enrichment_type="dns",
            status="queued",
            message=f"DNS lookup queued for {target.target_value}",
        )

    async def refresh_target_whois(self, target_id: str) -> EnrichmentRefreshResponse:
        target = await self._get_target_or_404(target_id)

        target.whois_status = TaskStatus.PENDING
        target.whois_error = None
        target.updated_at = utc_now()
        await self.session.commit()

        await self._activity.log_async(
            event=ActivityEvent.TARGET_ENRICHMENT_STARTED,
            title=f"WHOIS re-enrichment queued for {target.target_value}",
            target_id=target.id,
            project_id=target.project_id,
        )
        await self.session.commit()

        dispatch_whois_lookups([str(target.id)])

        return EnrichmentRefreshResponse(
            target_id=target.id,
            enrichment_type="whois",
            status="queued",
            message=f"WHOIS lookup queued for {target.target_value}",
        )

    async def refresh_target_bgp(self, target_id: str) -> EnrichmentRefreshResponse:
        target = await self._get_target_or_404(target_id)

        if target.target_type not in BGP_ELIGIBLE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"BGP enrichment is not applicable for target type '{target.target_type.value}'. "
                f"Only IP, IP range, and ASN targets support BGP enrichment.",
            )

        target.bgp_status = TaskStatus.PENDING
        target.updated_at = utc_now()
        await self.session.commit()

        dispatch_ripestat_enrichment([str(target.id)])

        await self._activity.log_async(
            event=ActivityEvent.TARGET_ENRICHMENT_STARTED,
            title=f"BGP re-enrichment queued for {target.target_value}",
            target_id=target.id,
            project_id=target.project_id,
        )
        await self.session.commit()

        return EnrichmentRefreshResponse(
            target_id=target.id,
            enrichment_type="bgp",
            status="queued",
            message=f"BGP enrichment queued for {target.target_value}",
        )

    async def _get_target_or_404(self, target_id: str) -> Target:
        try:
            UUID(target_id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid target ID format",
            ) from e
        result = await self.session.execute(
            select(Target).where(Target.id == target_id)
        )
        target = result.scalar_one_or_none()
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target not found",
            )
        return target

    async def _get_project_by_slug(self, slug: str) -> Project | None:
        result = await self.session.execute(select(Project).where(Project.slug == slug))
        return result.scalar_one_or_none()

    async def _get_organization_by_slug(self, slug: str) -> Organization | None:
        result = await self.session.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    async def _check_duplicate_target(self, target_value: str, project_id: str) -> None:
        existing_target = await self.session.execute(
            select(Target).where(
                Target.target_value == target_value,
                Target.project_id == project_id,
            )
        )

        if existing_target.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Target already exists in this project",
            )

    async def _get_or_create_organizations(
        self, org_names: list[str], project_id: str, user_id: str
    ) -> list[Organization]:
        organizations = []
        for org_name in org_names:
            org = await get_or_create_organization(
                org_name, project_id, user_id, self.session
            )
            organizations.append(org)
        return organizations

    async def _get_or_create_tags(
        self, tag_names: list[str], project_id: str, user_id: str
    ) -> list[Tag]:
        tags = []
        for tag_name in tag_names:
            tag = await get_or_create_tag(tag_name, project_id, user_id, self.session)
            tags.append(tag)
        return tags

    async def _process_bulk_target(
        self,
        target_value: str,
        project_id: str,
        user_id: str,
        organizations: list[Organization],
        tags: list[Tag],
        existing_target_values: set[str],
        seen_in_batch: set[str],
    ) -> "BulkTargetResult":
        _target_value = target_value.strip()

        if not _target_value:
            return BulkTargetResult(
                import_result=TargetImportResult(
                    target_value=_target_value,
                    success=False,
                    error="Empty target value",
                )
            )

        if _target_value in seen_in_batch:
            return BulkTargetResult(
                import_result=TargetImportResult(
                    target_value=_target_value,
                    success=False,
                    error="Duplicate within import batch",
                )
            )

        if _target_value in existing_target_values:
            return BulkTargetResult(
                import_result=TargetImportResult(
                    target_value=_target_value,
                    success=False,
                    error="Target already exists in project",
                )
            )

        target_type = validate_target(_target_value)
        if not target_type:
            return BulkTargetResult(
                import_result=TargetImportResult(
                    target_value=_target_value,
                    success=False,
                    error="Invalid target format",
                )
            )

        target = Target(
            target_value=_target_value,
            target_type=target_type,
            display_name=_target_value,
            project_id=project_id,
            created_by=user_id,
            organizations=organizations,
            tags=tags,
        )
        self.session.add(target)

        seen_in_batch.add(_target_value)
        existing_target_values.add(_target_value)

        return BulkTargetResult(
            import_result=TargetImportResult(
                target_value=_target_value,
                success=True,
                target_type=target_type,
                target_id=target.id,
            ),
            target=target,
        )

    async def _process_import_item(
        self,
        item: TargetImportItem,
        project_id: str,
        user_id: str,
        existing_target_values: set[str],
        seen_in_batch: set[str],
    ) -> "BulkTargetResult":
        target_value = item.target_value.strip()

        if not target_value:
            return BulkTargetResult(
                import_result=TargetImportResult(
                    target_value=target_value,
                    success=False,
                    error="Empty target value",
                )
            )

        if target_value in seen_in_batch:
            return BulkTargetResult(
                import_result=TargetImportResult(
                    target_value=target_value,
                    success=False,
                    error="Duplicate within import batch",
                )
            )

        if target_value in existing_target_values:
            return BulkTargetResult(
                import_result=TargetImportResult(
                    target_value=target_value,
                    success=False,
                    error="Target already exists in project",
                )
            )

        target_type = validate_target(target_value)
        if not target_type:
            return BulkTargetResult(
                import_result=TargetImportResult(
                    target_value=target_value,
                    success=False,
                    error="Invalid target format",
                )
            )

        organizations = []
        for org_name in item.organizations:
            if org_name.strip():
                org = await get_or_create_organization(
                    org_name.strip(), project_id, user_id, self.session
                )
                organizations.append(org)

        tags = []
        for tag_name in item.tags:
            if tag_name.strip():
                tag = await get_or_create_tag(
                    tag_name.strip(), project_id, user_id, self.session
                )
                tags.append(tag)

        target = Target(
            target_value=target_value,
            target_type=target_type,
            display_name=item.display_name or target_value,
            project_id=project_id,
            created_by=user_id,
            organizations=organizations,
            tags=tags,
        )
        self.session.add(target)

        seen_in_batch.add(target_value)
        existing_target_values.add(target_value)

        return BulkTargetResult(
            import_result=TargetImportResult(
                target_value=target_value,
                success=True,
                target_type=target_type,
                target_id=target.id,
            ),
            target=target,
        )

    def _to_target_read(self, target: Target) -> TargetRead:
        whois = None
        if target.whois_record:
            whois = WhoisRecordSummary(
                id=target.whois_record.id,
                query_value=target.whois_record.query_value,
                lookup_type=target.whois_record.lookup_type,
                name=target.whois_record.name,
                registrant_name=target.whois_record.registrant_name,
                registrar_name=target.whois_record.registrar_name,
                country=target.whois_record.country,
                network_cidr=target.whois_record.network_cidr,
                registration_date=target.whois_record.registration_date,
                expiration_date=target.whois_record.expiration_date,
                queried_at=target.whois_record.queried_at,
            )

        bgp = None
        if target.bgp_summary:
            bgp = BgpSummaryRead(
                prefix_count=target.bgp_summary.prefix_count,
                peer_count=target.bgp_summary.peer_count,
                announced=target.bgp_summary.announced,
                asn=target.bgp_summary.asn,
                prefix=target.bgp_summary.prefix,
                holder=target.bgp_summary.holder,
                queried_at=target.bgp_summary.queried_at,
            )

        dns = None
        if target.dns_lookup:
            dns = DnsxService.to_lookup_summary(target.dns_lookup)

        return TargetRead(
            **target.model_dump(
                exclude={
                    "organizations",
                    "tags",
                    "whois_record_id",
                    "whois_record",
                    "bgp_summary",
                }
            ),
            whois_record_id=target.whois_record_id,
            whois=whois,
            bgp=bgp,
            dns=dns,
            organizations=[
                OrganizationSummary(id=org.id, name=org.name, slug=org.slug)
                for org in target.organizations
            ],
            tags=[
                TagSummary(id=tag.id, name=tag.name, slug=tag.slug, color=tag.color)
                for tag in target.tags
            ],
        )

    def _to_dns_lookup_read(self, lookup: DnsLookup) -> DnsLookupRead:
        record_counts: dict[str, int] = {}
        records: list[DnsRecordRead] = []

        if lookup.records:
            counts = Counter(r.record_type.value for r in lookup.records)
            record_counts = dict(counts)
            records = [
                DnsRecordRead(
                    id=r.id,
                    record_type=r.record_type,
                    value=r.value,
                    priority=r.priority,
                    weight=r.weight,
                    port=r.port,
                    soa_email=r.soa_email,
                    soa_serial=r.soa_serial,
                    caa_tag=r.caa_tag,
                    caa_flag=r.caa_flag,
                )
                for r in lookup.records
            ]

        return DnsLookupRead(
            id=lookup.id,
            host=lookup.host,
            status_code=lookup.status_code,
            cdn=lookup.cdn,
            cdn_name=lookup.cdn_name,
            queried_at=lookup.queried_at,
            record_counts=record_counts,
            records=records,
        )

    async def _build_bgp_detail(self, target: Target) -> TargetBgpDetailResponse:
        summary = None
        if target.bgp_summary:
            summary = BgpSummaryRead(
                prefix_count=target.bgp_summary.prefix_count,
                peer_count=target.bgp_summary.peer_count,
                announced=target.bgp_summary.announced,
                asn=target.bgp_summary.asn,
                prefix=target.bgp_summary.prefix,
                holder=target.bgp_summary.holder,
                queried_at=target.bgp_summary.queried_at,
            )

        response = TargetBgpDetailResponse(
            target_id=target.id,
            target_type=target.target_type,
            status=target.bgp_status,
            summary=summary,
        )

        if target.target_type not in BGP_ELIGIBLE_TYPES:
            return response

        if target.target_type == TargetType.ASN:
            asn_number = int(target.target_value.upper().replace("AS", "").strip())

            overview_result = await self.session.execute(
                select(RIPEStatASOverview).where(RIPEStatASOverview.asn == asn_number)
            )
            overview = overview_result.scalar_one_or_none()
            if overview:
                response.as_overview = ASOverviewDetail(
                    asn=overview.asn,
                    holder=overview.holder,
                    rir=overview.rir,
                    announced=overview.announced,
                    block_name=overview.block_name,
                    block_resource=overview.block_resource,
                )

            prefixes_result = await self.session.execute(
                select(RIPEStatAnnouncedPrefix).where(
                    RIPEStatAnnouncedPrefix.asn == asn_number
                )
            )
            response.announced_prefixes = [
                AnnouncedPrefixDetail(
                    prefix=p.prefix,
                    ip_version=p.ip_version,
                    first_seen=p.first_seen,
                    last_seen=p.last_seen,
                )
                for p in prefixes_result.scalars().all()
            ]

            neighbours_result = await self.session.execute(
                select(RIPEStatASNNeighbour).where(
                    RIPEStatASNNeighbour.asn == asn_number
                )
            )
            response.neighbours = [
                ASNNeighbourDetail(
                    neighbour_asn=n.neighbour_asn,
                    relationship=n.relationship,
                    power=n.power,
                )
                for n in neighbours_result.scalars().all()
            ]

            abuse_result = await self.session.execute(
                select(RIPEStatAbuseContact).where(
                    RIPEStatAbuseContact.resource == f"AS{asn_number}"
                )
            )
            response.abuse_contacts = [
                AbuseContactDetail(
                    resource=a.resource,
                    abuse_email=a.abuse_email,
                    rir=a.rir,
                )
                for a in abuse_result.scalars().all()
            ]

        elif target.target_type == TargetType.IP:
            ip = target.target_value.strip()

            net_result = await self.session.execute(
                select(RIPEStatNetworkInfo).where(RIPEStatNetworkInfo.ip == ip)
            )
            net_rows = net_result.scalars().all()
            response.network_info = [
                NetworkInfoDetail(ip=n.ip, prefix=n.prefix, asn=n.asn) for n in net_rows
            ]

            if net_rows and net_rows[0].asn:
                overview_result = await self.session.execute(
                    select(RIPEStatASOverview).where(
                        RIPEStatASOverview.asn == net_rows[0].asn
                    )
                )
                overview = overview_result.scalar_one_or_none()
                if overview:
                    response.as_overview = ASOverviewDetail(
                        asn=overview.asn,
                        holder=overview.holder,
                        rir=overview.rir,
                        announced=overview.announced,
                        block_name=overview.block_name,
                        block_resource=overview.block_resource,
                    )

            abuse_result = await self.session.execute(
                select(RIPEStatAbuseContact).where(RIPEStatAbuseContact.resource == ip)
            )
            response.abuse_contacts = [
                AbuseContactDetail(
                    resource=a.resource,
                    abuse_email=a.abuse_email,
                    rir=a.rir,
                )
                for a in abuse_result.scalars().all()
            ]

        elif target.target_type == TargetType.IP_RANGE:
            prefix = target.target_value.strip()

            po_result = await self.session.execute(
                select(RIPEStatPrefixOverview).where(
                    RIPEStatPrefixOverview.prefix == prefix
                )
            )
            po_rows = po_result.scalars().all()
            response.prefix_overview = [
                PrefixOverviewDetail(
                    prefix=p.prefix,
                    asn=p.asn,
                    holder=p.holder,
                    is_announced=p.is_announced,
                )
                for p in po_rows
            ]

            if po_rows and po_rows[0].asn:
                overview_result = await self.session.execute(
                    select(RIPEStatASOverview).where(
                        RIPEStatASOverview.asn == po_rows[0].asn
                    )
                )
                overview = overview_result.scalar_one_or_none()
                if overview:
                    response.as_overview = ASOverviewDetail(
                        asn=overview.asn,
                        holder=overview.holder,
                        rir=overview.rir,
                        announced=overview.announced,
                        block_name=overview.block_name,
                        block_resource=overview.block_resource,
                    )

            rp_result = await self.session.execute(
                select(RIPEStatRelatedPrefix).where(
                    RIPEStatRelatedPrefix.prefix == prefix
                )
            )
            response.related_prefixes = [
                RelatedPrefixDetail(
                    related_prefix=r.related_prefix,
                    relationship=r.relationship,
                    origin_asn=r.origin_asn,
                )
                for r in rp_result.scalars().all()
            ]

            abuse_result = await self.session.execute(
                select(RIPEStatAbuseContact).where(
                    RIPEStatAbuseContact.resource == prefix
                )
            )
            response.abuse_contacts = [
                AbuseContactDetail(
                    resource=a.resource,
                    abuse_email=a.abuse_email,
                    rir=a.rir,
                )
                for a in abuse_result.scalars().all()
            ]

        return response

    def _parse_csv_to_targets(self, csv_text: str) -> list[TargetImportItem]:
        csv_reader = csv.DictReader(io.StringIO(csv_text))

        if csv_reader.fieldnames is None or not csv_reader.fieldnames:
            csv_reader = csv.reader(io.StringIO(csv_text))
            targets_data = [
                TargetImportItem(target_value=row[0].strip())
                for row in csv_reader
                if row and row[0].strip()
            ]
        else:
            fieldnames = [field.lower().strip() for field in csv_reader.fieldnames]

            targets_data = []
            for row in csv_reader:
                if not any(row.values()):
                    continue

                target_value = None
                for key in ["target_value", "target", "value", "domain", "ip"]:
                    if key in fieldnames:
                        idx = fieldnames.index(key)
                        orig_key = csv_reader.fieldnames[idx]
                        target_value = row.get(orig_key, "").strip()
                        break

                if not target_value:
                    continue

                tags = []
                for key in ["tags", "tag"]:
                    if key in fieldnames:
                        idx = fieldnames.index(key)
                        orig_key = csv_reader.fieldnames[idx]
                        tags_str = row.get(orig_key, "").strip()
                        if tags_str:
                            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                        break

                organizations = []
                for key in ["organizations", "organization", "orgs", "org"]:
                    if key in fieldnames:
                        idx = fieldnames.index(key)
                        orig_key = csv_reader.fieldnames[idx]
                        orgs_str = row.get(orig_key, "").strip()
                        if orgs_str:
                            organizations = [
                                o.strip() for o in orgs_str.split(",") if o.strip()
                            ]
                        break

                display_name = None
                for key in ["display_name", "name"]:
                    if key in fieldnames:
                        idx = fieldnames.index(key)
                        orig_key = csv_reader.fieldnames[idx]
                        display_name = row.get(orig_key, "").strip() or None
                        break

                targets_data.append(
                    TargetImportItem(
                        target_value=target_value,
                        tags=tags,
                        organizations=organizations,
                        display_name=display_name,
                    )
                )

        return targets_data

    def _dispatch_post_target_creation(self, targets: list[Target]) -> None:
        if not targets:
            return

        all_ids = [str(t.id) for t in targets]
        dispatch_whois_lookups(all_ids)

        dns_ids = [str(t.id) for t in targets if t.target_type in DNS_ELIGIBLE_TYPES]
        if dns_ids:
            dispatch_dns_lookups(dns_ids)

        bgp_ids = [str(t.id) for t in targets if t.target_type in BGP_ELIGIBLE_TYPES]
        if bgp_ids:
            dispatch_ripestat_enrichment(bgp_ids)
