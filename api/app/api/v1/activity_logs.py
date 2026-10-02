from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.pagination import Page
from app.core.database import get_session
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
    query = select(ActivityLog)
    if project_id:
        query = query.where(ActivityLog.project_id == project_id)
    query = query.order_by(ActivityLog.timestamp.desc())

    return await paginate(session, query)
