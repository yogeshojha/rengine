from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.v1.bounty_programs import _require_mode
from app.core.database import get_session
from app.services.bounty_report import BountyReportService, tracked_platform
from shared.definitions.bounty_reports import ReportSort
from shared.models.bounty_report import (
    BountyAccountSummary,
    BountyReportRead,
    ProgramReports,
)
from shared.services.celery_dispatch import dispatch_bounty_report_sync

router = APIRouter(prefix="/bounty-reports", tags=["bounty reports"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
PlatformPath = Annotated[str, Path(description="Bug bounty platform key")]


@router.get("/{platform}/summary", response_model=BountyAccountSummary)
async def summary(
    session: SessionDep, _current_user: CurrentUser, platform: PlatformPath
) -> BountyAccountSummary:
    """Reports, bounties and standing for the connected account."""
    await _require_mode(session)
    return await BountyReportService(session).summary(tracked_platform(platform))


@router.get("/{platform}/programs", response_model=list[ProgramReports])
async def programs(
    session: SessionDep, _current_user: CurrentUser, platform: PlatformPath
) -> list[ProgramReports]:
    """Every program the account reported to."""
    await _require_mode(session)
    return await BountyReportService(session).programs(tracked_platform(platform))


class ReportFilters:
    def __init__(
        self,
        state: Annotated[list[str] | None, Query()] = None,
        program: Annotated[
            list[str] | None, Query(description="Program handle")
        ] = None,
        severity: Annotated[list[str] | None, Query()] = None,
        q: str | None = Query(None),
        submitted_from: Annotated[datetime | None, Query()] = None,
        submitted_to: Annotated[datetime | None, Query()] = None,
    ) -> None:
        self.values = {
            "states": state,
            "programs": program,
            "severities": severity,
            "q": q,
            "submitted_from": submitted_from,
            "submitted_to": submitted_to,
        }


FiltersDep = Annotated[ReportFilters, Depends()]


@router.get("/{platform}/counts")
async def counts(
    session: SessionDep,
    _current_user: CurrentUser,
    platform: PlatformPath,
    filters: FiltersDep,
) -> dict[str, int]:
    """Report counts per tab under the active filters."""
    await _require_mode(session)
    spec = tracked_platform(platform)
    return await BountyReportService(session).counts(spec.key, **filters.values)


@router.get("/{platform}", response_model=Page[BountyReportRead])
async def list_reports(
    session: SessionDep,
    _current_user: CurrentUser,
    platform: PlatformPath,
    filters: FiltersDep,
    stage: str | None = Query(None, description="open, resolved or closed"),
    paid: bool | None = Query(None, description="Reports with a bounty"),
    sort: Annotated[ReportSort, Query()] = ReportSort.SUBMITTED,
    order: str = Query("desc", pattern="^(asc|desc)$"),
) -> Page[BountyReportRead]:
    await _require_mode(session)
    spec = tracked_platform(platform)
    service = BountyReportService(session)
    query = service.list_query(
        spec.key,
        stage=stage,
        paid=paid,
        sort=sort.value,
        order=order,
        **filters.values,
    )
    page = await paginate(session, query)
    page.items = await service.to_read(spec, list(page.items))
    return page


@router.post("/{platform}/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync(
    session: SessionDep, _current_user: CurrentUser, platform: PlatformPath
) -> dict:
    await _require_mode(session)
    spec = tracked_platform(platform)
    if not dispatch_bounty_report_sync(spec.key):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Refresh not queued. Check that the worker and Redis are running.",
        )
    return {"queued": True}
