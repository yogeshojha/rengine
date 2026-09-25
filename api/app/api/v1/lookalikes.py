from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.lookalikes import LookalikeService
from shared.models.lookalike import LookalikeSummary, LookalikeTriageUpdate
from shared.models.target import Target

router = APIRouter(prefix="/lookalikes", tags=["lookalikes"])


class TriageResult(BaseModel):
    updated: int


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LookalikeService:
    return LookalikeService(session)


@router.get("", response_model=LookalikeSummary)
async def scan_lookalikes(
    _current_user: CurrentUser,
    service: Annotated[LookalikeService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
    scan_id: Annotated[UUID, Query(description="Scan ID")],
):
    """Registered lookalikes of one scan."""
    return await service.for_scan(project_id, scan_id)


@router.get("/target/{target_id}", response_model=LookalikeSummary)
async def target_lookalikes(
    _current_user: CurrentUser,
    service: Annotated[LookalikeService, Depends(get_service)],
    target_id: UUID,
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    """The target's newest settled run that checked lookalikes."""
    return await service.for_target(project_id, target_id)


@router.patch("/triage", response_model=TriageResult)
async def triage_lookalikes(
    _current_user: CurrentUser,
    service: Annotated[LookalikeService, Depends(get_service)],
    body: LookalikeTriageUpdate,
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    """Set the review state of lookalikes of one target."""
    owned = await service.session.scalar(
        select(Target.id).where(
            Target.id == body.target_id, Target.project_id == project_id
        )
    )
    if owned is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Target not found.")
    updated = await service.triage(
        project_id, body.target_id, body.domains, body.state.value
    )
    return TriageResult(updated=updated)
