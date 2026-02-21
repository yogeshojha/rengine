from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.models.activity_log import ActivityLog, ActivityLogRead

router = APIRouter(
    prefix="/activity",
    tags=["activity"],
)


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
