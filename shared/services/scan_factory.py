import uuid

from shared.enums.scan import ScanScope, ScanStatus
from shared.enums.scan_context import AuthType
from shared.models.scan import Scan
from shared.services import target_seeds
from shared.services.proxy_resolve import scan_proxy_url
from shared.services.scan_resolve import (
    ResolvedScanConfig,
    _mask_auth,
    merge_engine_context,
    seal_run_config,
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
    run_group_id: uuid.UUID | None = None,
    dimension: str | None = None,
) -> Scan:
    """Assemble an unsaved PENDING Scan from an already-resolved config."""
    execution_config = seal_run_config(resolved.model_dump())
    if dimension:
        execution_config["_dimension"] = dimension
    execution_config["_auth_header_names"] = list(resolved._auth_header_names)
    execution_config["_auth"] = (
        _mask_auth(context.auth)
        if context is not None
        else {"auth_type": AuthType.NONE.value}
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
        scope=(ScanScope.FOCUSED.value if resolved.seed_only else ScanScope.FULL.value),
        parent_scan_id=parent_scan_id,
        run_group_id=run_group_id,
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
    intensity: str | None = None,
) -> Scan:
    """Resolve engine/context/target on a sync Session and flush a PENDING Scan."""
    from shared.models.scan_context import ScanContext  # noqa: PLC0415
    from shared.models.scan_engine import ScanEngine  # noqa: PLC0415
    from shared.models.target import Target  # noqa: PLC0415

    engine = session.get(ScanEngine, engine_id)
    if engine is None or engine.project_id != project_id:
        msg = "Scan engine not found."
        raise ScanFactoryError(msg)

    context = None
    if context_id is not None:
        context = session.get(ScanContext, context_id)
        if context is None or context.project_id != project_id:
            msg = "Scan context not found."
            raise ScanFactoryError(msg)

    target = session.get(Target, target_id)
    if target is None or target.project_id != project_id:
        msg = "Target not found."
        raise ScanFactoryError(msg)

    proxy_url = scan_proxy_url(session, context)

    resolved = merge_engine_context(
        engine,
        context,
        target.target_value,
        target.target_type.value,
        proxy_url=proxy_url,
        intensity=intensity,
    )
    if target.seed_scans:
        stored = target_seeds.load_sync(session, [target.id])
        target_seeds.apply(resolved, stored.get(target.id) or [], seed_only=False)
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
