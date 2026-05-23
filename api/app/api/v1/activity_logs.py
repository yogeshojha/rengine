from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.models.activity_log import ActivityLog, ActivityLogRead

router = APIRouter(
    prefix="/activity",
    tags=["activity"],
)


class ActivityDeleteResponse(BaseModel):
    deleted: int


@router.get("", response_model=Page[ActivityLogRead])
async def list_activity_logs(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_id: Annotated[str | None, Query(description="Filter by project ID")] = None,
    target_id: Annotated[str | None, Query(description="Filter by target ID")] = None,
    level: Annotated[
        ActivityLevel | None, Query(description="Filter by severity level")
    ] = None,
    event_type: Annotated[
        ActivityEvent | None, Query(description="Filter by event type")
    ] = None,
):
    """List activity log entries with optional filters.

    Scope is determined by filters:
      - target_id -> target-level activity
      - project_id (no target_id) -> project-level activity
      - no filters -> all activity (system-wide)
    """
    query = select(ActivityLog)

    if target_id:
        query = query.where(ActivityLog.target_id == target_id)
    elif project_id:
        query = query.where(ActivityLog.project_id == project_id)

    if level:
        query = query.where(ActivityLog.level == level)

    if event_type:
        query = query.where(ActivityLog.event_type == event_type)

    query = query.order_by(ActivityLog.timestamp.desc())

    return await paginate(session, query)


@router.delete("", response_model=ActivityDeleteResponse)
async def delete_activity_logs(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_id: Annotated[
        str | None, Query(description="Delete logs for a specific project")
    ] = None,
    target_id: Annotated[
        str | None, Query(description="Delete logs for a specific target")
    ] = None,
    level: Annotated[
        ActivityLevel | None, Query(description="Delete logs of a specific level")
    ] = None,
    event_type: Annotated[
        ActivityEvent | None, Query(description="Delete logs of a specific event type")
    ] = None,
):
    """Delete activity log entries matching the given filters.

    At least one filter is required to prevent accidental full wipes.
    """
    if not project_id and not target_id and not level and not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one filter (project_id, target_id, level, or event_type) is required",
        )

    stmt = delete(ActivityLog)

    if target_id:
        stmt = stmt.where(ActivityLog.target_id == target_id)
    elif project_id:
        stmt = stmt.where(ActivityLog.project_id == project_id)

    if level:
        stmt = stmt.where(ActivityLog.level == level)

    if event_type:
        stmt = stmt.where(ActivityLog.event_type == event_type)

    # count before delete
    count_query = select(func.count()).select_from(ActivityLog)
    if target_id:
        count_query = count_query.where(ActivityLog.target_id == target_id)
    elif project_id:
        count_query = count_query.where(ActivityLog.project_id == project_id)
    if level:
        count_query = count_query.where(ActivityLog.level == level)
    if event_type:
        count_query = count_query.where(ActivityLog.event_type == event_type)

    result = await session.execute(count_query)
    count = result.scalar_one()

    await session.execute(stmt)
    await session.commit()

    return ActivityDeleteResponse(deleted=count)
