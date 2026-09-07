from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.services.target import TargetService
from shared.definitions.bounty_programs import (
    DEFAULT_SYNC_INTERVAL,
    MAX_TAGS_PER_IMPORT,
    NOTIFIABLE_EVENTS,
    PLATFORMS_BY_KEY,
    SYNC_INTERVAL_HOURS,
    ProgramState,
    ScopeState,
    SubmissionState,
    SyncInterval,
    asset_type_spec,
    event_spec,
    notify_enabled,
    notify_events,
    raw_state_label,
)
from shared.enums.api_key import APIProvider
from shared.models.api_key import APIKey
from shared.models.bounty_program import (
    BountyEventRead,
    BountyEventRow,
    BountyImportRequest,
    BountyImportResult,
    BountyProgram,
    BountyProgramDetail,
    BountyProgramRead,
    BountyScope,
    BountyScopeRead,
    BountySettingsRead,
    BountySettingsUpdate,
    BountyStatus,
)
from shared.models.instance_settings import InstanceSettings
from shared.models.organization import Organization, OrganizationSummary
from shared.models.tag import Tag, TagSummary, TargetTag
from shared.models.target import Target, TargetOrganization
from shared.utils.datetime import utc_now
from shared.utils.slug import add_with_unique_slug
from shared.utils.validation import clean_name

MAX_ORG_NAME = 100
MAX_TAG_NAME = 50
DEFAULT_TAG_COLOR = "#6B7280"
MAX_ORG_DESCRIPTION = 500

EMPTY_COUNTS = {"in_scope_count": 0, "out_of_scope_count": 0, "importable_count": 0}


def _without_counts(program) -> dict:
    """paginate() may hand back an already-coerced read, so drop the tallies it defaulted."""
    data = program.model_dump()
    for key in (
        *EMPTY_COUNTS,
        "imported_count",
        "scopes",
        "unreachable",
        "raw_state_label",
    ):
        data.pop(key, None)
    data["raw_state_label"] = raw_state_label(data.get("raw_state"))
    return data


SORTS = {
    "name": (col(BountyProgram.name), "asc"),
    "reports": (col(BountyProgram.reports_for_user), "desc"),
    "age": (col(BountyProgram.started_accepting_at), "desc"),
    "assets": (col(BountyProgram.name), "asc"),
}


class BountyProgramService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _credentials_username(self) -> str | None:
        row = await self.session.execute(
            select(APIKey).where(APIKey.provider == APIProvider.HACKERONE)
        )
        key = row.scalar_one_or_none()
        if not key or not key.is_enabled:
            return None
        return (key.key_meta or {}).get("username")

    async def _settings(self) -> InstanceSettings | None:
        rows = await self.session.execute(select(InstanceSettings).limit(1))
        return rows.scalar_one_or_none()

    async def events(
        self, platform: str, *, kind: str | None, handle: str | None
    ) -> Select:
        query = select(BountyEventRow).where(BountyEventRow.platform == platform)
        if kind:
            query = query.where(BountyEventRow.kind == kind)
        if handle:
            query = query.where(BountyEventRow.handle == handle)
        return query.order_by(col(BountyEventRow.created_at).desc())

    @staticmethod
    def event_read(row: BountyEventRow) -> BountyEventRead:
        spec = event_spec(row.kind)
        return BountyEventRead(
            id=row.id,
            platform=row.platform,
            handle=row.handle,
            program_name=row.program_name,
            kind=row.kind,
            label=spec.label,
            description=spec.description,
            icon=spec.icon,
            tone=spec.tone,
            actionable=spec.actionable,
            asset_type=row.asset_type,
            asset_identifier=row.asset_identifier,
            detail=row.detail,
            created_at=row.created_at,
        )

    async def read_settings(self, platform: str) -> BountySettingsRead:
        settings = await self._settings()
        interval = (
            settings.bounty_sync_interval if settings else None
        ) or DEFAULT_SYNC_INTERVAL
        stored = settings.bounty_settings if settings else {}
        synced_at = settings.bounty_synced_at if settings else None
        hours = SYNC_INTERVAL_HOURS.get(interval)
        totals = await self.session.execute(
            select(
                select(func.count(BountyProgram.id))
                .where(BountyProgram.platform == platform)
                .scalar_subquery(),
                select(func.count(BountyEventRow.id))
                .where(BountyEventRow.platform == platform)
                .scalar_subquery(),
            )
        )
        programs, events = totals.one()
        return BountySettingsRead(
            sync_interval=interval,
            notify=notify_enabled(stored),
            notify_events=sorted(notify_events(stored)),
            notifiable_events=list(NOTIFIABLE_EVENTS),
            last_synced_at=synced_at,
            next_sync_at=(
                (synced_at + timedelta(hours=hours)) if (hours and synced_at) else None
            ),
            programs=programs or 0,
            events_recorded=events or 0,
        )

    async def write_settings(
        self, data: BountySettingsUpdate, platform: str
    ) -> BountySettingsRead:
        settings = await self._settings()
        if settings is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instance settings not found",
            )
        if data.sync_interval is not None:
            if data.sync_interval not in {i.value for i in SyncInterval}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown sync interval: {data.sync_interval}",
                )
            settings.bounty_sync_interval = data.sync_interval
        stored = dict(settings.bounty_settings or {})
        if data.notify is not None:
            stored["notify"] = data.notify
        if data.notify_events is not None:
            unknown = set(data.notify_events) - set(NOTIFIABLE_EVENTS)
            if unknown:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown change kinds: {', '.join(sorted(unknown))}",
                )
            stored["notify_events"] = sorted(set(data.notify_events))
        settings.bounty_settings = stored
        await self.session.commit()
        return await self.read_settings(platform)

    async def mark_events_seen(self) -> None:
        settings = await self._settings()
        if settings:
            settings.bounty_events_seen_at = utc_now()
            await self.session.commit()

    async def status(self, platform: str) -> BountyStatus:
        username = await self._credentials_username()
        settings = await self._settings()
        interval = (settings.bounty_sync_interval if settings else None) or (
            DEFAULT_SYNC_INTERVAL
        )
        synced_at = settings.bounty_synced_at if settings else None
        seen_at = settings.bounty_events_seen_at if settings else None
        hours = SYNC_INTERVAL_HOURS.get(interval)
        next_sync = (
            (synced_at + timedelta(hours=hours)) if (hours and synced_at) else None
        )
        unseen = await self.session.execute(
            select(func.count(BountyEventRow.id)).where(
                BountyEventRow.platform == platform,
                *([BountyEventRow.created_at > seen_at] if seen_at else []),
            )
        )
        totals = await self.session.execute(
            select(
                func.count(BountyProgram.id),
                func.count(BountyProgram.id).filter(
                    BountyProgram.program_state == ProgramState.PRIVATE.value
                ),
                func.max(BountyProgram.synced_at),
            ).where(BountyProgram.platform == platform)
        )
        total, private, last = totals.one()
        return BountyStatus(
            configured=bool(username),
            platform=platform,
            username=username,
            programs=total or 0,
            private_programs=private or 0,
            last_synced_at=synced_at or last,
            sync_interval=interval,
            next_sync_at=next_sync,
            unseen_events=unseen.scalar_one() or 0,
        )

    def _filtered(
        self,
        platform: str,
        *,
        q: str | None,
        state: str | None,
        submission: str | None,
        bounty: bool | None,
        bookmarked: bool | None,
        joined: bool | None,
        scope: str | None,
    ) -> Select:
        query = select(BountyProgram).where(BountyProgram.platform == platform)
        if q:
            term = f"%{q.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(BountyProgram.name).like(term),
                    func.lower(BountyProgram.handle).like(term),
                )
            )
        if state in {s.value for s in ProgramState}:
            query = query.where(BountyProgram.program_state == state)
        if submission in {s.value for s in SubmissionState}:
            query = query.where(BountyProgram.submission_state == submission)
        if bounty is not None:
            query = query.where(BountyProgram.offers_bounties == bounty)
        if bookmarked is not None:
            query = query.where(BountyProgram.bookmarked == bookmarked)
        if joined is not None:
            query = query.where(BountyProgram.joined == joined)
        if scope == "importable":
            query = query.where(
                select(BountyScope.id)
                .where(
                    BountyScope.program_id == BountyProgram.id,
                    BountyScope.scope_state == ScopeState.IN_SCOPE.value,
                    col(BountyScope.target_value).is_not(None),
                )
                .exists()
            )
        elif scope == "none":
            query = query.where(
                ~select(BountyScope.id)
                .where(BountyScope.program_id == BountyProgram.id)
                .exists()
            )
        return query

    def list_query(self, platform: str, *, sort: str, **filters) -> Select:
        query = self._filtered(platform, **filters)
        column, default_dir = SORTS.get(sort or "age", SORTS["age"])
        ordering = column.desc() if default_dir == "desc" else column.asc()
        return query.order_by(ordering.nullslast(), col(BountyProgram.name).asc())

    async def imported_for(
        self, program_ids: list[UUID], project_id: UUID | None
    ) -> dict[UUID, int]:
        """How many of each program's assets the project already tracks."""
        if not program_ids or not project_id:
            return {}
        rows = await self.session.execute(
            select(
                BountyScope.program_id,
                func.count(func.distinct(BountyScope.target_value)),
            )
            .join(
                Target,
                (Target.target_value == BountyScope.target_value)
                & (Target.project_id == project_id),
            )
            .where(col(BountyScope.program_id).in_(program_ids))
            .group_by(BountyScope.program_id)
        )
        return {program_id: count or 0 for program_id, count in rows.all()}

    async def counts_for(self, program_ids: list[UUID]) -> dict[UUID, dict[str, int]]:
        """Scope tallies per program, so a card can state what it holds before it opens."""
        if not program_ids:
            return {}
        rows = await self.session.execute(
            select(
                BountyScope.program_id,
                func.count(BountyScope.id),
                func.count(BountyScope.id).filter(
                    BountyScope.scope_state == ScopeState.IN_SCOPE.value
                ),
                func.count(BountyScope.id).filter(
                    col(BountyScope.target_value).is_not(None),
                    BountyScope.scope_state == ScopeState.IN_SCOPE.value,
                ),
            )
            .where(col(BountyScope.program_id).in_(program_ids))
            .group_by(BountyScope.program_id)
        )
        out: dict[UUID, dict[str, int]] = {}
        for program_id, total, in_scope, importable in rows.all():
            out[program_id] = {
                "in_scope_count": in_scope or 0,
                "out_of_scope_count": (total or 0) - (in_scope or 0),
                "importable_count": importable or 0,
            }
        return out

    async def to_read(
        self, programs: list[BountyProgram], project_id: UUID | None = None
    ) -> list[BountyProgramRead]:
        ids = [p.id for p in programs]
        counts = await self.counts_for(ids)
        imported = await self.imported_for(ids, project_id)
        return [
            BountyProgramRead(
                **_without_counts(p),
                **counts.get(p.id, EMPTY_COUNTS),
                imported_count=imported.get(p.id, 0),
            )
            for p in programs
        ]

    async def get_program(self, platform: str, handle: str) -> BountyProgram:
        row = await self.session.execute(
            select(BountyProgram).where(
                BountyProgram.platform == platform, BountyProgram.handle == handle
            )
        )
        program = row.scalar_one_or_none()
        if not program:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Program not found"
            )
        return program

    async def detail(
        self,
        platform: str,
        handle: str,
        *,
        project_id: UUID | None,
        scope: str | None = None,
        asset_type: str | None = None,
    ) -> BountyProgramDetail:
        program = await self.get_program(platform, handle)
        query = select(BountyScope).where(BountyScope.program_id == program.id)
        if scope in {s.value for s in ScopeState}:
            query = query.where(BountyScope.scope_state == scope)
        if asset_type:
            query = query.where(BountyScope.asset_type == asset_type.upper())
        rows = (await self.session.execute(query)).scalars().all()

        existing: set[str] = set()
        if project_id:
            values = [s.target_value for s in rows if s.target_value]
            if values:
                found = await self.session.execute(
                    select(Target.target_value).where(
                        Target.project_id == project_id,
                        col(Target.target_value).in_(values),
                    )
                )
                existing = set(found.scalars().all())

        scopes = [self._scope_read(s, existing) for s in rows]
        scopes.sort(
            key=lambda s: (
                s.scope_state != ScopeState.IN_SCOPE.value,
                not s.importable,
                s.asset_identifier,
            )
        )
        counts = await self.counts_for([program.id])
        unreachable: dict[str, int] = {}
        for s in rows:
            if s.target_value:
                continue
            label = asset_type_spec(s.asset_type).label
            unreachable[label] = unreachable.get(label, 0) + 1
        return BountyProgramDetail(
            **_without_counts(program),
            **counts.get(program.id, EMPTY_COUNTS),
            imported_count=len(existing),
            scopes=scopes,
            unreachable=unreachable,
        )

    @staticmethod
    def _scope_read(scope: BountyScope, existing: set[str]) -> BountyScopeRead:
        spec = asset_type_spec(scope.asset_type)
        return BountyScopeRead(
            id=scope.id,
            asset_type=scope.asset_type,
            asset_type_label=spec.label,
            asset_group=spec.group.value,
            icon=spec.icon,
            asset_identifier=scope.asset_identifier,
            scope_state=scope.scope_state,
            eligible_for_bounty=scope.eligible_for_bounty,
            max_severity=scope.max_severity,
            instruction=scope.instruction,
            target_value=scope.target_value,
            target_type=scope.target_type.value if scope.target_type else None,
            importable=bool(scope.target_value),
            already_target=bool(scope.target_value and scope.target_value in existing),
        )

    async def import_scopes(
        self, platform: str, handle: str, request: BountyImportRequest, user_id
    ) -> BountyImportResult:
        """Add a program's scannable assets to a project as targets."""
        program = await self.get_program(platform, handle)
        query = select(BountyScope).where(
            BountyScope.program_id == program.id,
            col(BountyScope.target_value).is_not(None),
        )
        if request.scope_ids:
            query = query.where(col(BountyScope.id).in_(request.scope_ids))
        if not request.include_out_of_scope:
            query = query.where(BountyScope.scope_state == ScopeState.IN_SCOPE.value)
        rows = (await self.session.execute(query)).scalars().all()

        skipped = sorted(
            {
                s.asset_identifier
                for s in (await self._all_scopes(program.id))
                if not s.target_value
            }
        )
        values = sorted({s.target_value for s in rows if s.target_value})
        if not values:
            return BountyImportResult(created=[], existing=[], skipped=skipped)

        before = await self.session.execute(
            select(Target.target_value).where(
                Target.project_id == request.project_id,
                col(Target.target_value).in_(values),
            )
        )
        already = set(before.scalars().all())
        targets = TargetService(self.session)
        rows = await targets.ensure_targets(values, request.project_id, user_id)

        organization = None
        if request.group_by_program:
            organization = await self._organization_for(
                program, request.project_id, user_id, request.organization_name
            )
            await self._attach(rows, organization)
        tags = await self._tags_for(request, program, user_id)
        await self._attach_tags(rows, tags)
        await self.session.commit()
        return BountyImportResult(
            created=[v for v in values if v not in already],
            existing=sorted(already),
            skipped=skipped,
            organization=(
                OrganizationSummary(
                    id=organization.id, name=organization.name, slug=organization.slug
                )
                if organization
                else None
            ),
            tags=[
                TagSummary(id=t.id, name=t.name, slug=t.slug, color=t.color)
                for t in tags
            ],
        )

    async def _tags_for(
        self, request: BountyImportRequest, program: BountyProgram, user_id
    ) -> list[Tag]:
        """The project's tags for these names, created on first use."""
        spec = PLATFORMS_BY_KEY.get(program.platform)
        wanted: dict[str, str] = {}
        for raw in request.tags[:MAX_TAGS_PER_IMPORT]:
            name = clean_name(raw, max_len=MAX_TAG_NAME).lower()
            if name:
                wanted.setdefault(name, DEFAULT_TAG_COLOR)
        if spec and spec.tag in wanted:
            wanted[spec.tag] = spec.tag_color
        if not wanted:
            return []

        found = await self.session.execute(
            select(Tag).where(
                Tag.project_id == request.project_id, col(Tag.name).in_(list(wanted))
            )
        )
        tags = {t.name: t for t in found.scalars().all()}
        for name, color in wanted.items():
            if name in tags:
                continue
            tag = Tag(
                name=name,
                color=color,
                project_id=request.project_id,
                created_by=user_id,
            )
            try:
                await add_with_unique_slug(
                    self.session, tag, name, project_id=request.project_id
                )
            except IntegrityError:
                await self.session.rollback()
                again = await self.session.execute(
                    select(Tag).where(
                        Tag.project_id == request.project_id, Tag.name == name
                    )
                )
                tags[name] = again.scalar_one()
                continue
            tags[name] = tag
        return [tags[name] for name in wanted if name in tags]

    async def _attach_tags(self, targets: list[Target], tags: list[Tag]) -> None:
        """A tag already on a target must not fail the import."""
        if not targets or not tags:
            return
        await self.session.execute(
            pg_insert(TargetTag)
            .values(
                [{"target_id": t.id, "tag_id": tag.id} for t in targets for tag in tags]
            )
            .on_conflict_do_nothing()
        )

    async def _organization_for(
        self,
        program: BountyProgram,
        project_id: UUID,
        user_id,
        override: str | None = None,
    ) -> Organization:
        """The project's organization for this program, created on first import."""
        chosen = (override or "").strip() or program.name
        name = clean_name(chosen, max_len=MAX_ORG_NAME).lower()
        found = await self.session.execute(
            select(Organization).where(
                Organization.project_id == project_id, Organization.name == name
            )
        )
        existing = found.scalar_one_or_none()
        if existing:
            return existing
        organization = Organization(
            name=name,
            description=f"HackerOne program @{program.handle}"[:MAX_ORG_DESCRIPTION],
            project_id=project_id,
            created_by=user_id,
        )
        try:
            await add_with_unique_slug(
                self.session, organization, name, project_id=project_id
            )
        except IntegrityError:
            await self.session.rollback()
            again = await self.session.execute(
                select(Organization).where(
                    Organization.project_id == project_id, Organization.name == name
                )
            )
            return again.scalar_one()
        return organization

    async def _attach(self, targets: list[Target], organization: Organization) -> None:
        """A target already under the organization must not fail the import."""
        if not targets:
            return
        await self.session.execute(
            pg_insert(TargetOrganization)
            .values(
                [
                    {"target_id": t.id, "organization_id": organization.id}
                    for t in targets
                ]
            )
            .on_conflict_do_nothing()
        )

    async def _all_scopes(self, program_id: UUID) -> list[BountyScope]:
        rows = await self.session.execute(
            select(BountyScope).where(BountyScope.program_id == program_id)
        )
        return list(rows.scalars().all())

    @staticmethod
    def require_platform(platform: str) -> str:
        if platform not in PLATFORMS_BY_KEY:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown platform: {platform}",
            )
        return platform
