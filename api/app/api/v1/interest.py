from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.interest import InterestError, InterestReadService, catalog
from shared.models.interest import (
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
from shared.services.celery_dispatch import (
    dispatch_interest_evaluation,
    dispatch_interest_refresh,
)

router = APIRouter(prefix="/interest", tags=["interest"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _scan(session: AsyncSession, scan_id: UUID) -> Scan:
    scan = await session.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")
    return scan


@router.get("/catalog", response_model=InterestCatalog)
async def get_catalog(_user: CurrentUser) -> InterestCatalog:
    return catalog()


@router.get("/rules", response_model=list[InterestRuleRead])
async def list_rules(
    session: SessionDep,
    _user: CurrentUser,
    project_id: Annotated[UUID, Query()],
) -> list[InterestRuleRead]:
    return await InterestReadService(session).rules(project_id)


@router.post(
    "/rules", response_model=InterestRuleRead, status_code=status.HTTP_201_CREATED
)
async def create_rule(
    session: SessionDep,
    user: CurrentUser,
    payload: InterestRuleCreate,
    project_id: Annotated[UUID, Query()],
) -> InterestRuleRead:
    try:
        rule = await InterestReadService(session).create(payload, project_id, user.id)
    except InterestError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    dispatch_interest_refresh(str(project_id))
    return rule


@router.patch("/rules/{rule_id}", response_model=InterestRuleRead)
async def update_rule(
    session: SessionDep,
    _user: CurrentUser,
    rule_id: Annotated[UUID, Path()],
    payload: InterestRuleUpdate,
    project_id: Annotated[UUID, Query()],
) -> InterestRuleRead:
    try:
        rule = await InterestReadService(session).update(rule_id, payload)
    except InterestError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    dispatch_interest_refresh(str(project_id))
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    session: SessionDep,
    _user: CurrentUser,
    rule_id: Annotated[UUID, Path()],
    project_id: Annotated[UUID, Query()],
) -> None:
    if not await InterestReadService(session).delete(rule_id):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Rule not found, or it is a shipped rule"
        )
    dispatch_interest_refresh(str(project_id))


@router.post("/rules/preview", response_model=RulePreview)
async def preview_rule(
    session: SessionDep,
    _user: CurrentUser,
    query: Annotated[str, Body(embed=True)],
    scan_id: Annotated[UUID | None, Query()] = None,
) -> RulePreview:
    return await InterestReadService(session).preview(query, scan_id)


@router.post("/scan/{scan_id}", response_model=InterestPage)
async def scan_interest(
    session: SessionDep,
    _user: CurrentUser,
    scan_id: Annotated[UUID, Path()],
    body: InterestFilter,
) -> InterestPage:
    scan = await _scan(session, scan_id)
    service = InterestReadService(session)
    page = await service.page(scan, body)
    # a rule changed since this scan was labelled; refresh in the background, never on the read
    if page.summary.stale:
        dispatch_interest_evaluation(str(scan_id), include_ai=False)
    return page


@router.post("/scan/{scan_id}/judge", status_code=status.HTTP_202_ACCEPTED)
async def judge_scan(
    session: SessionDep,
    _user: CurrentUser,
    scan_id: Annotated[UUID, Path()],
) -> dict:
    await _scan(session, scan_id)
    dispatch_interest_evaluation(str(scan_id), include_ai=True)
    return {"status": "queued"}


@router.get("/scan/{scan_id}/suggestions", response_model=list[RuleSuggestion])
async def rule_suggestions(
    session: SessionDep,
    _user: CurrentUser,
    scan_id: Annotated[UUID, Path()],
) -> list[RuleSuggestion]:
    scan = await _scan(session, scan_id)
    return await InterestReadService(session).suggestions(scan)


@router.post("/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss(
    session: SessionDep,
    user: CurrentUser,
    payload: DismissRequest,
) -> None:
    from shared.models.target import Target  # noqa: PLC0415

    target = await session.get(Target, payload.target_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target not found")
    await InterestReadService(session).dismiss(
        target_id=payload.target_id,
        project_id=target.project_id,
        host=payload.host,
        kind=payload.kind or "",
        note=payload.note,
        user_id=user.id,
    )


@router.get("/dismissals", response_model=list[dict])
async def list_dismissals(
    session: SessionDep,
    _user: CurrentUser,
    target_id: Annotated[UUID | None, Query()] = None,
    project_id: Annotated[UUID | None, Query()] = None,
) -> list[dict]:
    if target_id is None and project_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Name a target or a project")
    rows = await InterestReadService(session).dismissals(
        target_id=target_id, project_id=project_id
    )
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
) -> None:
    if not await InterestReadService(session).restore(dismissal_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
