from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from app.services.oast import OastService
from shared.models.oast import OastRead, OastTest, OastUpdate

router = APIRouter(prefix="/oast", tags=["out-of-band testing"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OastService:
    return OastService(session)


@router.get("", response_model=OastRead)
async def read_oast(
    _current_user: CurrentUser,
    service: Annotated[OastService, Depends(get_service)],
):
    return await service.read()


@router.patch("", response_model=OastRead)
async def update_oast(
    _current_user: CurrentSuperuser,
    service: Annotated[OastService, Depends(get_service)],
    body: OastUpdate,
):
    return await service.update(body)


@router.post("/reset", response_model=OastRead)
async def reset_oast(
    _current_user: CurrentSuperuser,
    service: Annotated[OastService, Depends(get_service)],
):
    """Clear the server, the token and the acknowledgement."""
    return await service.reset()


@router.post("/test", response_model=OastTest)
async def test_oast(
    _current_user: CurrentSuperuser,
    service: Annotated[OastService, Depends(get_service)],
):
    """Check that the configured server answers."""
    return await service.test()
