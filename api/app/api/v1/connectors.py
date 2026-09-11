from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.scope import EndpointScope
from app.core.client_ip import client_id
from app.core.database import get_session
from app.core.ratelimit import clear_failures, record_failure, too_many_attempts
from app.services.connector import ConnectorError, ConnectorService, _guard
from app.services.endpoint import EndpointService
from connectors import auth
from shared.models.connector import (
    ActionRead,
    ActionRequest,
    AddTargetRequest,
    CandidatePage,
    ConnectorCoverage,
    ConnectorCreate,
    ConnectorCreated,
    ConnectorRead,
    ConnectorScope,
    ConnectorUpdate,
    DiscoveredDomain,
    EndpointActionRequest,
    FindingRecorded,
    FindingReport,
    HostFacts,
    IngestRequest,
    IngestResult,
    NoticeRead,
    SessionRead,
    TargetAdded,
    TargetOption,
)
from shared.models.endpoint import Endpoint
from shared.models.scan import ScanRead

router = APIRouter(prefix="/connectors", tags=["connectors"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConnectorService:
    return ConnectorService(session)


TOKEN_ATTEMPT_LIMIT = 20
TOKEN_ATTEMPT_WINDOW = 900


async def _authenticate(
    service: ConnectorService, request: Request, header: str | None
):
    key = f"connector:token:{client_id(request)}"
    await too_many_attempts(key, limit=TOKEN_ATTEMPT_LIMIT)
    row = await service.authenticate(auth.from_header(header))
    if row is None:
        await record_failure(key, window_seconds=TOKEN_ATTEMPT_WINDOW)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown connector token."
        )
    await clear_failures(key)
    return row


def _base(request: Request) -> str:
    """The URL the proxy must reach."""
    return str(request.base_url).rstrip("/")


Service = Annotated[ConnectorService, Depends(get_service)]
ProjectId = Annotated[UUID, Query(description="Project ID")]


@router.post("/ingest", response_model=IngestResult)
async def ingest(
    payload: IngestRequest,
    service: Service,
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
):
    """The endpoint a proxy posts to. Authenticated by connector token, never a user session."""
    row = await _authenticate(service, request, authorization)
    return await service.ingest(row, payload)


@router.get("/actions", response_model=list[ActionRead])
async def collect_actions(
    service: Service,
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
):
    """Collected by the proxy, not pushed to it. Authenticated by connector token."""
    row = await _authenticate(service, request, authorization)
    return await service.take_actions(row)


@router.post("/{connector_id}/send")
async def send_to_proxy(
    connector_id: UUID,
    body: ActionRequest,
    _current_user: CurrentUser,
    service: Service,
    project_id: ProjectId,
):
    try:
        queued = await service.queue_actions(
            connector_id, project_id, body.ids, body.kind
        )
    except ConnectorError as exc:
        raise _guard(exc) from exc
    return {"queued": queued}


@router.post("/{connector_id}/send-endpoints")
async def send_endpoints_to_proxy(
    connector_id: UUID,
    body: EndpointActionRequest,
    _current_user: CurrentUser,
    service: Service,
    project_id: ProjectId,
    scope: EndpointScope,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Discovered endpoints, chosen by id or by filter, into the proxy's Repeater."""
    if body.endpoint_ids:
        rows = list(
            (
                await session.execute(
                    select(Endpoint).where(
                        Endpoint.id.in_(body.endpoint_ids),
                        Endpoint.project_id == project_id,
                    )
                )
            )
            .scalars()
            .all()
        )
    elif body.filter is not None:
        rows = await EndpointService(session).pick(scope, body.filter, body.limit)
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Pass endpoint_ids or a filter.",
        )
    try:
        queued = await service.queue_endpoint_actions(
            connector_id, project_id, rows, body.kind
        )
    except ConnectorError as exc:
        raise _guard(exc) from exc
    return {"queued": queued}


@router.get("/targets", response_model=list[TargetOption])
async def picker_targets(
    service: Service,
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
):
    """The targets the proxy offers while testing. Authenticated by connector token."""
    row = await _authenticate(service, request, authorization)
    return await service.target_options(row)


@router.get("/notices", response_model=list[NoticeRead])
async def collect_notices(
    service: Service,
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
):
    """What reNgine wants said while the tester is still testing. Delivered once."""
    row = await _authenticate(service, request, authorization)
    return await service.take_notices(row)


@router.post("/findings", response_model=FindingRecorded)
async def report_finding(
    body: FindingReport,
    service: Service,
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
):
    """A finding a person confirmed by hand, reported from the proxy."""
    row = await _authenticate(service, request, authorization)
    try:
        return await service.record_finding(row, body, row.created_by)
    except ConnectorError as exc:
        raise _guard(exc) from exc


@router.get("/scope", response_model=ConnectorScope)
async def target_scope(
    service: Service,
    request: Request,
    target_id: UUID | None = None,
    program_id: UUID | None = None,
    authorization: Annotated[str | None, Header()] = None,
):
    """Scope rules the proxy applies to its own target scope."""
    row = await _authenticate(service, request, authorization)
    if (target_id is None) == (program_id is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Give either a target or a program.",
        )
    try:
        if program_id is not None:
            return await service.program_scope(row, program_id)
        return await service.scope_for(row, target_id)
    except ConnectorError as exc:
        raise _guard(exc) from exc


@router.get("/host", response_model=HostFacts)
async def host_facts(
    service: Service,
    request: Request,
    host: str,
    authorization: Annotated[str | None, Header()] = None,
):
    """What reNgine already knows about the host being tested."""
    row = await _authenticate(service, request, authorization)
    try:
        return await service.host_facts(row, host)
    except ConnectorError as exc:
        raise _guard(exc) from exc


@router.get("/catalog")
async def catalog(_current_user: CurrentUser, service: Service):
    return service.catalog()


@router.get("", response_model=list[ConnectorRead])
async def list_connectors(
    _current_user: CurrentUser, service: Service, project_id: ProjectId
):
    return await service.list(project_id)


@router.post("", response_model=ConnectorCreated, status_code=status.HTTP_201_CREATED)
async def create_connector(
    data: ConnectorCreate, current_user: CurrentUser, service: Service, request: Request
):
    try:
        return await service.create(data, current_user.id, _base(request))
    except ConnectorError as exc:
        raise _guard(exc) from exc


@router.patch("/{connector_id}", response_model=ConnectorRead)
async def update_connector(
    connector_id: UUID,
    data: ConnectorUpdate,
    _current_user: CurrentUser,
    service: Service,
    project_id: ProjectId,
):
    try:
        return await service.update(connector_id, project_id, data)
    except ConnectorError as exc:
        raise _guard(exc) from exc


@router.post("/{connector_id}/rotate", response_model=ConnectorCreated)
async def rotate_token(
    connector_id: UUID,
    _current_user: CurrentUser,
    service: Service,
    project_id: ProjectId,
    request: Request,
):
    return await service.rotate(connector_id, project_id, _base(request))


@router.delete("/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connector(
    connector_id: UUID,
    _current_user: CurrentUser,
    service: Service,
    project_id: ProjectId,
):
    await service.delete(connector_id, project_id)


@router.get("/{connector_id}/candidates", response_model=CandidatePage)
async def candidates(
    connector_id: UUID,
    _current_user: CurrentUser,
    service: Service,
    project_id: ProjectId,
    state: str | None = None,
    host: str | None = None,
    notice: str | None = None,
    search: str | None = None,
    page: int = 1,
):
    return await service.candidates(
        connector_id,
        project_id,
        state=state,
        host=host,
        notice=notice,
        search=search,
        page=page,
    )


@router.post("/{connector_id}/candidates/state")
async def set_candidate_state(
    connector_id: UUID,
    body: dict,
    _current_user: CurrentUser,
    service: Service,
    project_id: ProjectId,
):
    try:
        changed = await service.set_state(
            connector_id,
            project_id,
            [UUID(i) for i in body.get("ids", [])],
            body.get("state", ""),
        )
    except ConnectorError as exc:
        raise _guard(exc) from exc
    return {"changed": changed}


@router.delete("/{connector_id}/candidates")
async def clear_candidates(
    connector_id: UUID,
    _current_user: CurrentUser,
    service: Service,
    project_id: ProjectId,
):
    return {"removed": await service.clear(connector_id, project_id)}


@router.post("/{connector_id}/scan", response_model=ScanRead)
async def scan_queue(
    connector_id: UUID,
    body: dict,
    current_user: CurrentUser,
    service: Service,
    project_id: ProjectId,
):
    try:
        return await service.scan(
            connector_id,
            project_id,
            current_user.id,
            [UUID(i) for i in body.get("ids", [])] or None,
        )
    except ConnectorError as exc:
        raise _guard(exc) from exc


@router.get("/{connector_id}/coverage", response_model=list[ConnectorCoverage])
async def coverage(
    connector_id: UUID,
    _current_user: CurrentUser,
    service: Service,
    project_id: ProjectId,
):
    return await service.coverage(connector_id, project_id)


@router.get("/{connector_id}/discovered", response_model=list[DiscoveredDomain])
async def discovered(
    connector_id: UUID,
    _current_user: CurrentUser,
    service: Service,
    project_id: ProjectId,
):
    return await service.discovered(connector_id, project_id)


@router.post("/{connector_id}/discovered/add", response_model=TargetAdded)
async def add_discovered_target(
    connector_id: UUID,
    body: AddTargetRequest,
    current_user: CurrentUser,
    service: Service,
    project_id: ProjectId,
):
    try:
        return await service.add_target(
            connector_id, project_id, current_user.id, body.domain, body.scan
        )
    except ConnectorError as exc:
        raise _guard(exc) from exc


@router.post("/{connector_id}/discovered/dismiss")
async def dismiss_discovered(
    connector_id: UUID,
    body: AddTargetRequest,
    _current_user: CurrentUser,
    service: Service,
    project_id: ProjectId,
):
    return {
        "dismissed": await service.dismiss_domain(connector_id, project_id, body.domain)
    }


@router.get("/{connector_id}/sessions", response_model=list[SessionRead])
async def sessions(
    connector_id: UUID,
    _current_user: CurrentUser,
    service: Service,
    project_id: ProjectId,
):
    return await service.sessions(connector_id, project_id)
