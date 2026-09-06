from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.report import ReportService
from shared.definitions.reports import FORMAT_MEDIA_TYPES, ReportFormat
from shared.models.report import (
    ReportCatalog,
    ReportCreate,
    ReportEstimate,
    ReportRead,
    ReportTemplateCreate,
    ReportTemplateRead,
    ReportTemplateUpdate,
    ReportThemeRead,
    ReportThemeUpload,
)

router = APIRouter(prefix="/reports", tags=["reports"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/catalog", response_model=ReportCatalog)
async def report_catalog(_current_user: CurrentUser, session: Session):
    return await ReportService(session).catalog()


@router.get("/themes", response_model=list[ReportThemeRead])
async def list_themes(_current_user: CurrentUser, session: Session):
    return await ReportService(session).themes()


@router.get("/themes/{slug}/source", response_model=str)
async def theme_source(
    _current_user: CurrentUser,
    session: Session,
    slug: Annotated[str, Path(description="Theme key")],
):
    return await ReportService(session).theme_source(slug)


@router.post(
    "/themes", response_model=ReportThemeRead, status_code=status.HTTP_201_CREATED
)
async def upload_theme(
    current_user: CurrentUser, session: Session, body: ReportThemeUpload
):
    return await ReportService(session).upload_theme(body.content, current_user.id)


@router.delete("/themes/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_theme(
    _current_user: CurrentUser,
    session: Session,
    slug: Annotated[str, Path(description="Theme key")],
):
    await ReportService(session).delete_theme(slug)


@router.get("/templates", response_model=list[ReportTemplateRead])
async def list_templates(
    _current_user: CurrentUser,
    session: Session,
    project_id: Annotated[UUID, Query(description="Project")],
):
    return await ReportService(session).templates(project_id)


@router.post(
    "/templates", response_model=ReportTemplateRead, status_code=status.HTTP_201_CREATED
)
async def create_template(
    current_user: CurrentUser,
    session: Session,
    body: ReportTemplateCreate,
    project_id: Annotated[UUID, Query(description="Project")],
):
    return await ReportService(session).create_template(
        body, project_id, current_user.id
    )


@router.patch("/templates/{template_id}", response_model=ReportTemplateRead)
async def update_template(
    _current_user: CurrentUser,
    session: Session,
    template_id: Annotated[UUID, Path(description="Template")],
    body: ReportTemplateUpdate,
    project_id: Annotated[UUID, Query(description="Project")],
):
    return await ReportService(session).update_template(template_id, project_id, body)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    _current_user: CurrentUser,
    session: Session,
    template_id: Annotated[UUID, Path(description="Template")],
    project_id: Annotated[UUID, Query(description="Project")],
):
    await ReportService(session).delete_template(template_id, project_id)


@router.post("/estimate", response_model=ReportEstimate)
async def estimate_report(
    _current_user: CurrentUser,
    session: Session,
    body: ReportCreate,
    project_id: Annotated[UUID, Query(description="Project")],
):
    return await ReportService(session).estimate(body, project_id)


@router.get("", response_model=list[ReportRead])
async def list_reports(
    _current_user: CurrentUser,
    session: Session,
    project_id: Annotated[UUID, Query(description="Project")],
    scan_id: Annotated[
        UUID | None, Query(description="Only reports for this scan")
    ] = None,
    target_id: Annotated[
        UUID | None, Query(description="Only reports for this target")
    ] = None,
):
    return await ReportService(session).list(
        project_id, scan_id=scan_id, target_id=target_id
    )


@router.post("", response_model=ReportRead, status_code=status.HTTP_202_ACCEPTED)
async def create_report(
    current_user: CurrentUser,
    session: Session,
    body: ReportCreate,
    project_id: Annotated[UUID, Query(description="Project")],
):
    return await ReportService(session).create(body, project_id, current_user.id)


@router.get("/{report_id}", response_model=ReportRead)
async def get_report(
    _current_user: CurrentUser,
    session: Session,
    report_id: Annotated[UUID, Path(description="Report")],
    project_id: Annotated[UUID, Query(description="Project")],
):
    service = ReportService(session)
    return service.to_read(await service.get(report_id, project_id))


@router.post(
    "/{report_id}/retry",
    response_model=ReportRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_report(
    _current_user: CurrentUser,
    session: Session,
    report_id: Annotated[UUID, Path(description="Report")],
    project_id: Annotated[UUID, Query(description="Project")],
):
    return await ReportService(session).retry(report_id, project_id)


@router.get("/{report_id}/download")
async def download_report(
    _current_user: CurrentUser,
    session: Session,
    report_id: Annotated[UUID, Path(description="Report")],
    project_id: Annotated[UUID, Query(description="Project")],
    format: Annotated[
        str, Query(description="Which rendered format to download")
    ] = ReportFormat.PDF.value,
):
    service = ReportService(session)
    report = await service.get(report_id, project_id)
    path, filename = service.file_path(report, format)
    return FileResponse(
        path,
        media_type=FORMAT_MEDIA_TYPES.get(format, "application/octet-stream"),
        filename=filename,
    )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    _current_user: CurrentUser,
    session: Session,
    report_id: Annotated[UUID, Path(description="Report")],
    project_id: Annotated[UUID, Query(description="Project")],
):
    await ReportService(session).delete(report_id, project_id)
