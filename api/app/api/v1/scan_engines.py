from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.scan_engine import ScanEngineService, build_catalog, preview_engine
from shared.models.scan_engine import (
    EngineCatalog,
    EnginePreviewRequest,
    EnginePreviewResult,
    ScanEngineCreate,
    ScanEngineRead,
    ScanEngineUpdate,
)

router = APIRouter(
    prefix="/engines",
    tags=["scan-engines"],
)


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScanEngineService:
    return ScanEngineService(session)


class YamlBody(BaseModel):
    yaml: str


@router.get("/catalog", response_model=EngineCatalog)
async def engine_catalog(_current_user: CurrentUser):
    return build_catalog()


@router.post("/preview", response_model=EnginePreviewResult)
async def preview_engine_stages(
    data: EnginePreviewRequest,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await preview_engine(data, session)


@router.get("", response_model=list[ScanEngineRead])
async def list_engines(
    _current_user: CurrentUser,
    service: Annotated[ScanEngineService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.list(project_id)


@router.post("", response_model=ScanEngineRead, status_code=status.HTTP_201_CREATED)
async def create_engine(
    data: ScanEngineCreate,
    current_user: CurrentUser,
    service: Annotated[ScanEngineService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.create(
        project_id=project_id,
        created_by=current_user.id,
        data=data,
    )


@router.post(
    "/import", response_model=ScanEngineRead, status_code=status.HTTP_201_CREATED
)
async def import_engine(
    body: YamlBody,
    current_user: CurrentUser,
    service: Annotated[ScanEngineService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.import_yaml(
        project_id=project_id,
        created_by=current_user.id,
        yaml_str=body.yaml,
    )


@router.get("/{id}", response_model=ScanEngineRead)
async def get_engine(
    id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ScanEngineService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.get(id=id, project_id=project_id)


@router.patch("/{id}", response_model=ScanEngineRead)
async def update_engine(
    id: UUID,
    data: ScanEngineUpdate,
    _current_user: CurrentUser,
    service: Annotated[ScanEngineService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.update(id=id, project_id=project_id, data=data)


@router.delete("/{id}", response_model=dict)
async def delete_engine(
    id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ScanEngineService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    await service.delete(id=id, project_id=project_id)
    return {"deleted": True}


@router.post(
    "/{id}/duplicate",
    response_model=ScanEngineRead,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_engine(
    id: UUID,
    current_user: CurrentUser,
    service: Annotated[ScanEngineService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    return await service.duplicate(
        id=id, project_id=project_id, created_by=current_user.id
    )


@router.get("/{id}/export", response_model=dict)
async def export_engine(
    id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ScanEngineService, Depends(get_service)],
    project_id: Annotated[UUID, Query(description="Project ID")],
):
    yaml_str = await service.export_yaml(id=id, project_id=project_id)
    return {"yaml": yaml_str}
