from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, StreamUser
from app.api.v1.events import STREAM_HEADERS
from app.core.database import get_session
from app.services.investigate.service import InvestigateService, stream_run
from shared.models.investigate import (
    InvestigateBrief,
    InvestigateRequest,
    InvestigationRead,
    PlanDecision,
)

router = APIRouter(prefix="/investigate", tags=["investigate"])
Session = Annotated[AsyncSession, Depends(get_session)]
ProjectId = Annotated[UUID, Query(description="Project ID")]


def get_service(session: Session) -> InvestigateService:
    return InvestigateService(session)


Service = Annotated[InvestigateService, Depends(get_service)]


@router.get("/brief", response_model=InvestigateBrief)
async def brief(
    _user: CurrentUser,
    service: Service,
    project_id: ProjectId,
    scan_id: Annotated[UUID, Query(description="Scan ID")],
    fingerprint: Annotated[str, Query(min_length=1, max_length=500)],
):
    return await service.brief(project_id, scan_id, fingerprint)


@router.post("/run")
async def run(data: InvestigateRequest, user: StreamUser, project_id: ProjectId):
    return StreamingResponse(
        stream_run(user=user, project_id=project_id, request=data),
        media_type="text/event-stream",
        headers=STREAM_HEADERS,
    )


@router.post(
    "/approve", response_model=InvestigationRead, status_code=status.HTTP_200_OK
)
async def approve(
    data: PlanDecision, user: CurrentUser, service: Service, project_id: ProjectId
):
    return await service.approve(user, project_id, data.plan_ids)


@router.post("/decline", response_model=InvestigationRead)
async def decline(
    data: PlanDecision, _user: CurrentUser, service: Service, project_id: ProjectId
):
    return await service.decline(project_id, data.plan_ids)
