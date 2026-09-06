from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.vuln_template import VulnTemplateService
from shared.definitions.vulnerabilities import (
    PROTOCOL_LABELS,
    SEVERITY_HELP,
    SEVERITY_LABELS,
    SEVERITY_ORDER,
    SURFACE_LABELS,
    TEMPLATE_ORIGIN_LABELS,
    VULN_STATE_HELP,
    VULN_STATE_LABELS,
)
from shared.models.vuln_template import (
    SelectionPreview,
    TemplateFilter,
    TemplateLibraryStats,
    TemplatePage,
    TemplateSelection,
    TemplateSource,
    TemplateSourceUpdate,
    TemplateSyncResult,
    VulnTemplateRead,
    VulnTemplateUpdate,
    VulnTemplateUploadRequest,
    VulnTemplateUploadResult,
)
from shared.services.vuln_templates import TemplateError

router = APIRouter(prefix="/vuln-templates", tags=["vulnerability templates"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VulnTemplateService:
    return VulnTemplateService(session)


@router.get("/vocabulary")
async def template_vocabulary(_current_user: CurrentUser) -> dict:
    """The shared vocabulary the vulnerability UI renders from."""
    return {
        "severities": [
            {
                "value": name,
                "label": SEVERITY_LABELS[name],
                "description": SEVERITY_HELP[name],
            }
            for name in SEVERITY_ORDER
        ],
        "protocols": [
            {"value": value, "label": label} for value, label in PROTOCOL_LABELS.items()
        ],
        "states": [
            {
                "value": value,
                "label": label,
                "description": VULN_STATE_HELP.get(value, ""),
            }
            for value, label in VULN_STATE_LABELS.items()
        ],
        "origins": [
            {"value": value, "label": label}
            for value, label in TEMPLATE_ORIGIN_LABELS.items()
        ],
        "surfaces": [
            {"value": value, "label": label} for value, label in SURFACE_LABELS.items()
        ],
    }


@router.get("/stats", response_model=TemplateLibraryStats)
async def library_stats(
    _current_user: CurrentUser,
    service: Annotated[VulnTemplateService, Depends(get_service)],
):
    return await service.stats()


@router.post("/search", response_model=TemplatePage)
async def search_templates(
    _current_user: CurrentUser,
    service: Annotated[VulnTemplateService, Depends(get_service)],
    body: TemplateFilter,
):
    return await service.list(body)


@router.post("/selection", response_model=SelectionPreview)
async def preview_selection(
    _current_user: CurrentUser,
    service: Annotated[VulnTemplateService, Depends(get_service)],
    body: TemplateSelection,
):
    """Count what a vulnerability plan would run, before it runs."""
    return await service.preview(body)


@router.post("/sync", response_model=TemplateSyncResult)
async def sync_library(
    _current_user: CurrentUser,
    service: Annotated[VulnTemplateService, Depends(get_service)],
):
    return service.sync()


@router.post(
    "/upload",
    response_model=VulnTemplateUploadResult,
    status_code=status.HTTP_201_CREATED,
)
async def upload_templates(
    current_user: CurrentUser,
    service: Annotated[VulnTemplateService, Depends(get_service)],
    body: VulnTemplateUploadRequest,
):
    return await service.upload(body, current_user.id)


@router.get("/{template_id}", response_model=VulnTemplateRead)
async def get_template(
    _current_user: CurrentUser,
    service: Annotated[VulnTemplateService, Depends(get_service)],
    template_id: Annotated[UUID, Path(description="Template ID")],
):
    found = await service.get(template_id)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
    return found


@router.patch("/{template_id}", response_model=VulnTemplateRead)
async def update_template(
    _current_user: CurrentUser,
    service: Annotated[VulnTemplateService, Depends(get_service)],
    template_id: Annotated[UUID, Path(description="Template ID")],
    body: VulnTemplateUpdate,
):
    updated = await service.update(template_id, body)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
    return updated


@router.get("/{template_id}/source", response_model=TemplateSource)
async def read_source(
    _current_user: CurrentUser,
    service: Annotated[VulnTemplateService, Depends(get_service)],
    template_id: Annotated[UUID, Path(description="Template ID")],
):
    """The check exactly as the scanner will read it."""
    found = await service.source(template_id)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
    return found


@router.put("/{template_id}/source", response_model=VulnTemplateRead)
async def write_source(
    _current_user: CurrentUser,
    service: Annotated[VulnTemplateService, Depends(get_service)],
    template_id: Annotated[UUID, Path(description="Template ID")],
    body: TemplateSourceUpdate,
):
    try:
        updated = await service.rewrite(template_id, body.content)
    except TemplateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
    return updated


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    _current_user: CurrentUser,
    service: Annotated[VulnTemplateService, Depends(get_service)],
    template_id: Annotated[UUID, Path(description="Template ID")],
):
    if not await service.delete(template_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Only custom templates can be deleted.",
        )
