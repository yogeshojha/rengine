from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.pagination import Page
from app.core.database import get_session
from shared.definitions.activity import FEED_EVENTS
from shared.models.activity_log import ActivityLog, ActivityLogRead

router = APIRouter(
    prefix="/activity",
    tags=["activity"],
)


@router.get("", response_model=Page[ActivityLogRead])
async def list_activity_logs(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_id: Annotated[
        UUID | None, Query(description="Filter by project ID")
    ] = None,
):
    return await paginate(session, feed_query(project_id))


def feed_query(project_id: UUID | None):
    """The panel's rows: feed events of targets that still exist."""
    query = select(ActivityLog).where(
        ActivityLog.event_type.in_(FEED_EVENTS),
        or_(ActivityLog.target_id.isnot(None), ActivityLog.target_value.is_(None)),
    )
    if project_id:
        query = query.where(ActivityLog.project_id == project_id)
    return query.order_by(ActivityLog.timestamp.desc())
