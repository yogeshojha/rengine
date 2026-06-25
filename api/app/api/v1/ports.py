from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.port import PortService
from shared.models.port import PortRead, PortSummary

router = APIRouter(
    prefix="/ports",
    tags=["ports"],
)


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PortService:
    return PortService(session)


@router.get("", response_model=list[PortRead])
async def list_ports(
    _current_user: CurrentUser,
    service: Annotated[PortService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID | None, Query(description="Filter by scan ID")] = None,
    target_id: Annotated[UUID | None, Query(description="Filter by target ID")] = None,
    search: Annotated[str | None, Query(description="Substring match on IP")] = None,
    limit: Annotated[int, Query(ge=1, le=1000, description="Max rows")] = 1000,
    offset: Annotated[int, Query(ge=0, description="Rows to skip")] = 0,
):
    return await service.list(
        project_id=project_id,
        scan_id=scan_id,
        target_id=target_id,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/summary", response_model=PortSummary)
async def port_summary(
    _current_user: CurrentUser,
    service: Annotated[PortService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID | None, Query(description="Filter by scan ID")] = None,
    target_id: Annotated[UUID | None, Query(description="Filter by target ID")] = None,
):
    return await service.summary(
        project_id=project_id, scan_id=scan_id, target_id=target_id
    )
