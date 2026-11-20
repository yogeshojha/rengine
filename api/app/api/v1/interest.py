import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.access import Access, ProjectId, check_open, not_found, owned
from app.api.deps import CurrentUser
from app.api.scope import TargetFilterDep
from app.core.database import get_session
from app.services.interest import InterestError, InterestReadService, catalog
from app.services.surface_scope import SurfaceScopeService
from app.services.target_scope import resolve_targets
from shared.definitions.asset_query import MAX_QUERY_LENGTH
from shared.definitions.surface import SurfaceDimension
from shared.models.interest import (
    BulkDismissRequest,
    BulkDismissResult,
    DismissRequest,
    InterestCatalog,
    InterestFilter,
    InterestPage,
    InterestRuleCreate,
    InterestRuleRead,
    InterestRuleUpdate,
    RulePreview,
    RuleSuggestion,
)
from shared.models.scan import Scan
from shared.models.target import Target
from shared.services.asset_query import QueryScope
from shared.services.celery_dispatch import (
    dispatch_interest_evaluation,
    dispatch_interest_refresh,
)
from shared.services.project_access import ProjectSet, project_clause

router = APIRouter(prefix="/interest", tags=["interest"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _scan(session: AsyncSession, access: ProjectSet, scan_id: UUID) -> Scan:
    return await owned(session, access, Scan, scan_id, "Scan")


@router.get("/catalog", response_model=InterestCatalog)
async def get_catalog(_user: CurrentUser) -> InterestCatalog:
    return catalog()


@router.get("/rules", response_model=list[InterestRuleRead])
async def list_rules(
    session: SessionDep,
    _user: CurrentUser,
    project_id: ProjectId,
) -> list[InterestRuleRead]:
    return await InterestReadService(session).rules(project_id)


@router.post(
    "/rules", response_model=InterestRuleRead, status_code=status.HTTP_201_CREATED
)
async def create_rule(
    session: SessionDep,
    user: CurrentUser,
    payload: InterestRuleCreate,
    project_id: ProjectId,
) -> InterestRuleRead:
    try:
        rule = await InterestReadService(session).create(payload, project_id, user.id)
    except InterestError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await asyncio.to_thread(dispatch_interest_refresh, str(project_id))
    return rule


@router.patch("/rules/{rule_id}", response_model=InterestRuleRead)
async def update_rule(
    session: SessionDep,
    user: CurrentUser,
    rule_id: Annotated[UUID, Path()],
    payload: InterestRuleUpdate,
    project_id: ProjectId,
) -> InterestRuleRead:
    try:
        rule = await InterestReadService(session).update(
            rule_id, payload, project_id, superuser=user.is_superuser
        )
    except InterestError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found.")
    await asyncio.to_thread(dispatch_interest_refresh, str(project_id))
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    session: SessionDep,
    _user: CurrentUser,
    rule_id: Annotated[UUID, Path()],
    project_id: ProjectId,
) -> None:
    if not await InterestReadService(session).delete(rule_id, project_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found or read-only.")
    await asyncio.to_thread(dispatch_interest_refresh, str(project_id))


@router.post("/rules/preview", response_model=RulePreview)
async def preview_rule(
    session: SessionDep,
    _user: CurrentUser,
    access: Access,
    query: Annotated[str, Body(embed=True, max_length=MAX_QUERY_LENGTH)],
    scan_id: Annotated[UUID | None, Query()] = None,
    project_id: Annotated[UUID | None, Query()] = None,
) -> RulePreview:
    if project_id is not None:
        check_open(access, project_id)
    if scan_id is not None:
        scan = await _scan(session, access, scan_id)
        if project_id not in (None, scan.project_id):
            raise not_found(noun="Scan")
    return await InterestReadService(session).preview(query, scan_id, project_id)


@router.post("/scan/{scan_id}", response_model=InterestPage)
async def scan_interest(
    session: SessionDep,
    _user: CurrentUser,
    access: Access,
    scan_id: Annotated[UUID, Path()],
    body: InterestFilter,
) -> InterestPage:
    scan = await _scan(session, access, scan_id)
    service = InterestReadService(session)
    page = await service.page(
        QueryScope((scan.id,), project_id=scan.project_id), body, scan
    )
    if page.summary.stale:
        await asyncio.to_thread(
            dispatch_interest_evaluation, str(scan_id), include_ai=False
        )
    return page


@router.post("/project", response_model=InterestPage)
async def project_interest(
    session: SessionDep,
    _user: CurrentUser,
    project_id: ProjectId,
    body: InterestFilter,
    spec: TargetFilterDep,
) -> InterestPage:
    """Flagged assets across each target's latest covering scan."""
    targets = await resolve_targets(session, project_id, spec)
    if targets is not None and not set(spec.target_ids) <= targets:
        raise not_found(noun="Target")
    scope = await SurfaceScopeService(session).scope(
        project_id, SurfaceDimension.WEB_ASSETS.value, targets=targets
    )
    return await InterestReadService(session).page(scope, body)


@router.post("/scan/{scan_id}/judge", status_code=status.HTTP_202_ACCEPTED)
async def judge_scan(
    session: SessionDep,
    _user: CurrentUser,
    access: Access,
    scan_id: Annotated[UUID, Path()],
) -> dict:
    await _scan(session, access, scan_id)
    await asyncio.to_thread(dispatch_interest_evaluation, str(scan_id), include_ai=True)
    return {"status": "queued"}


@router.post("/scan/{scan_id}/suggestions", response_model=list[RuleSuggestion])
async def rule_suggestions(
    session: SessionDep,
    _user: CurrentUser,
    access: Access,
    scan_id: Annotated[UUID, Path()],
) -> list[RuleSuggestion]:
    scan = await _scan(session, access, scan_id)
    return await InterestReadService(session).suggestions(scan)


@router.post("/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss(
    session: SessionDep,
    user: CurrentUser,
    access: Access,
    payload: DismissRequest,
) -> None:
    target = await owned(session, access, Target, payload.target_id, "Target")
    await InterestReadService(session).dismiss(
        target_id=payload.target_id,
        project_id=target.project_id,
        host=payload.host,
        kind=payload.kind or "",
        note=payload.note,
        user_id=user.id,
    )


@router.post("/dismiss/bulk", response_model=BulkDismissResult)
async def dismiss_many(
    session: SessionDep,
    user: CurrentUser,
    access: Access,
    payload: BulkDismissRequest,
) -> BulkDismissResult:
    wanted = {row.target_id for row in payload.rows}
    targets = dict(
        (
            await session.execute(
                select(Target.id, Target.project_id).where(
                    Target.id.in_(wanted), project_clause(access, Target.project_id)
                )
            )
        ).all()
    )
    if wanted - targets.keys():
        raise not_found(noun="Target")
    count = await InterestReadService(session).dismiss_many(
        [
            (row.target_id, targets[row.target_id], row.host, row.kind or "")
            for row in payload.rows
        ],
        user.id,
    )
    return BulkDismissResult(dismissed=count)


@router.get("/dismissals", response_model=list[dict])
async def list_dismissals(
    session: SessionDep,
    _user: CurrentUser,
    project_id: ProjectId,
) -> list[dict]:
    rows = await InterestReadService(session).dismissals(project_id=project_id)
    return [
        {
            "id": str(row.id),
            "host": row.host,
            "kind": row.kind,
            "target_id": str(row.target_id),
            "note": row.note,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.delete("/dismissals/{dismissal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def restore_dismissal(
    session: SessionDep,
    _user: CurrentUser,
    dismissal_id: Annotated[UUID, Path()],
    project_id: ProjectId,
) -> None:
    if not await InterestReadService(session).restore(dismissal_id, project_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dismissal not found.")
