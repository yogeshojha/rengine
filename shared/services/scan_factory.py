import uuid

from shared.enums.scan import ScanScope, ScanStatus
from shared.models.scan import Scan
from shared.services.proxy_resolve import resolve_proxy_url
from shared.services.scan_resolve import (
    ResolvedScanConfig,
    _mask_auth,
    merge_engine_context,
)


class ScanFactoryError(Exception):
    pass


def build_scan_row(
    *,
    resolved: ResolvedScanConfig,
    engine,
    context,
    target,
    project_id: uuid.UUID,
    created_by: uuid.UUID,
    schedule_id: uuid.UUID | None = None,
    schedule_type: str | None = None,
    parent_scan_id: uuid.UUID | None = None,
    dimension: str | None = None,
) -> Scan:
    """Assemble an unsaved PENDING Scan from an already-resolved config."""
    execution_config = resolved.model_dump()
    if dimension:
        execution_config["_dimension"] = dimension
    execution_config["_auth_header_names"] = list(resolved._auth_header_names)
    execution_config["_auth"] = (
        _mask_auth(context.auth) if context is not None else {"auth_type": "none"}
    )
    return Scan(
        project_id=project_id,
        target_id=target.id,
        engine_id=engine.id,
        engine_name=engine.name,
        context_id=context.id if context is not None else None,
        context_name=context.name if context is not None else None,
        execution_config=execution_config,
        status=ScanStatus.PENDING.value,
        subdomains_found=0,
        ips_found=0,
        open_ports_found=0,
        vulnerabilities_found=0,
        endpoints_found=0,
        created_by=created_by,
        schedule_id=schedule_id,
        schedule_type=schedule_type,
        scope=(
            ScanScope.FOCUSED.value if resolved.seed_assets else ScanScope.FULL.value
        ),
        parent_scan_id=parent_scan_id,
    )


def build_scan_for_target_sync(
    session,
    *,
    project_id: uuid.UUID,
    target_id: uuid.UUID,
    engine_id: uuid.UUID,
    context_id: uuid.UUID | None,
    created_by: uuid.UUID,
    schedule_id: uuid.UUID | None = None,
    schedule_type: str | None = None,
) -> Scan:
    """Resolve engine/context/target on a sync Session and flush a PENDING Scan."""
    from shared.models.proxy import Proxy  # noqa: PLC0415
    from shared.models.scan_context import ScanContext  # noqa: PLC0415
    from shared.models.scan_engine import ScanEngine  # noqa: PLC0415
    from shared.models.target import Target  # noqa: PLC0415

    engine = session.get(ScanEngine, engine_id)
    if engine is None or engine.project_id != project_id:
        msg = "scan engine not found"
        raise ScanFactoryError(msg)

    context = None
    if context_id is not None:
        context = session.get(ScanContext, context_id)
        if context is None or context.project_id != project_id:
            msg = "scan context not found"
            raise ScanFactoryError(msg)

    target = session.get(Target, target_id)
    if target is None or target.project_id != project_id:
        msg = "target not found"
        raise ScanFactoryError(msg)

    proxy_url = None
    if context is not None and context.proxy_id is not None:
        proxy_url = resolve_proxy_url(session.get(Proxy, context.proxy_id))

    resolved = merge_engine_context(
        engine,
        context,
        target.target_value,
        target.target_type.value,
        proxy_url=proxy_url,
    )
    scan = build_scan_row(
        resolved=resolved,
        engine=engine,
        context=context,
        target=target,
        project_id=project_id,
        created_by=created_by,
        schedule_id=schedule_id,
        schedule_type=schedule_type,
    )
    session.add(scan)
    session.flush()
    return scan
