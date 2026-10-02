from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.api.scope import VulnScope
from app.core.database import get_session
from app.services.issue_tracking import IssueFilingService, IssueTrackerService
from shared.models.issue_tracker import (
    FileSelection,
    FilingPlan,
    FilingResult,
    IssueTrackerCreate,
    IssueTrackerRead,
    IssueTrackerTestConfig,
    IssueTrackerTestResult,
    IssueTrackerUpdate,
    RouteRead,
    RouteSet,
    TrackedIssueRead,
    TrackerOption,
)

router = APIRouter(prefix="/issue-trackers", tags=["issue-trackers"])

Session = Annotated[AsyncSession, Depends(get_session)]


def trackers(session: Session) -> IssueTrackerService:
    return IssueTrackerService(session)


def filing(session: Session, user: CurrentUser) -> IssueFilingService:
    return IssueFilingService(session, admin=user.is_superuser)


Trackers = Annotated[IssueTrackerService, Depends(trackers)]
Filing = Annotated[IssueFilingService, Depends(filing)]


@router.get("", response_model=list[IssueTrackerRead])
async def list_trackers(user: CurrentUser, service: Trackers):
    return await service.list(reveal=user.is_superuser)


@router.post("", response_model=IssueTrackerRead, status_code=status.HTTP_201_CREATED)
async def create_tracker(
    data: IssueTrackerCreate, user: CurrentSuperuser, service: Trackers
):
    return await service.create(data, user.id)


@router.post("/test", response_model=IssueTrackerTestResult)
async def test_tracker_config(
    data: IssueTrackerTestConfig, _user: CurrentSuperuser, service: Trackers
):
    return await service.test_config(data)


# ---------- routes ----------


@router.get("/routes", response_model=list[RouteRead])
async def list_routes(
    project_id: Annotated[UUID, Query(description="Project ID")],
    _user: CurrentUser,
    service: Trackers,
):
    return await service.routes(project_id)


@router.put("/routes", response_model=RouteRead)
async def set_route(data: RouteSet, _user: CurrentSuperuser, service: Trackers):
    return await service.set_route(data)


@router.delete("/routes/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_route(route_id: UUID, _user: CurrentSuperuser, service: Trackers):
    await service.delete_route(route_id)


# ---------- issues ----------


@router.get("/issues", response_model=list[TrackedIssueRead])
async def list_issues(
    project_id: Annotated[UUID, Query(description="Project ID")],
    _user: CurrentUser,
    service: Filing,
):
    return await service.list(project_id)


@router.post("/issues/plan", response_model=FilingPlan)
async def plan_issues(
    body: FileSelection, _user: CurrentUser, scope: VulnScope, service: Filing
):
    return await service.plan(scope, body)


@router.post(
    "/issues", response_model=FilingResult, status_code=status.HTTP_202_ACCEPTED
)
async def file_issues(
    body: FileSelection, user: CurrentUser, scope: VulnScope, service: Filing
):
    return await service.file(scope, body, user.id)


@router.post("/issues/{issue_id}/retry", response_model=TrackedIssueRead)
async def retry_issue(issue_id: UUID, _user: CurrentUser, service: Filing):
    return await service.retry(issue_id)


@router.post("/issues/{issue_id}/refresh", response_model=TrackedIssueRead)
async def refresh_issue(issue_id: UUID, _user: CurrentUser, service: Filing):
    return await service.refresh(issue_id)


@router.delete("/issues/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_issue(issue_id: UUID, _user: CurrentUser, service: Filing):
    await service.unlink(issue_id)


# ---------- one tracker ----------


@router.patch("/{tracker_id}", response_model=IssueTrackerRead)
async def update_tracker(
    tracker_id: UUID,
    data: IssueTrackerUpdate,
    _user: CurrentSuperuser,
    service: Trackers,
):
    return await service.update(tracker_id, data)


@router.delete("/{tracker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tracker(tracker_id: UUID, _user: CurrentSuperuser, service: Trackers):
    await service.delete(tracker_id)


@router.post("/{tracker_id}/test", response_model=IssueTrackerTestResult)
async def test_tracker(tracker_id: UUID, _user: CurrentSuperuser, service: Trackers):
    return await service.test(tracker_id)


@router.get("/{tracker_id}/destinations", response_model=list[TrackerOption])
async def tracker_destinations(
    tracker_id: UUID,
    _user: CurrentSuperuser,
    service: Trackers,
    q: Annotated[str, Query(max_length=100)] = "",
):
    return await service.destinations(tracker_id, q)


@router.get("/{tracker_id}/issue-types", response_model=list[TrackerOption])
async def tracker_issue_types(
    tracker_id: UUID,
    destination: Annotated[str, Query(max_length=200)],
    _user: CurrentSuperuser,
    service: Trackers,
):
    return await service.issue_types(tracker_id, destination)
