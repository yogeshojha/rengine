from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.access import OptionalProject
from app.api.deps import CurrentUser
from app.api.pagination import Page
from app.core.database import get_session
from shared.definitions.activity import FEED_EVENTS
from shared.models.activity_log import ActivityLog, ActivityLogRead
from shared.services.project_access import ProjectSet, scoped

router = APIRouter(
    prefix="/activity",
    tags=["activity"],
)


@router.get("", response_model=Page[ActivityLogRead])
async def list_activity_logs(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    projects: OptionalProject,
):
    return await apaginate(session, feed_query(projects))


def feed_query(projects: ProjectSet):
    """The panel's rows: feed events of targets that still exist."""
    query = select(ActivityLog).where(
        ActivityLog.event_type.in_(FEED_EVENTS),
        or_(ActivityLog.target_id.isnot(None), ActivityLog.target_value.is_(None)),
    )
    return scoped(query, projects, ActivityLog.project_id).order_by(
        ActivityLog.timestamp.desc()
    )
