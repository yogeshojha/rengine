from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scan_engine.validation import (
    _validate_global_threads,
    _validate_intensity,
    _validate_stages,
)
from shared.definitions.launch import ASSET_KIND_LABELS, seed_produces
from shared.enums.scan import Intensity
from shared.enums.target import TargetType
from shared.models.scan_context import ScanContext
from shared.models.scan_engine import EnginePreviewResult, PreviewResolved
from shared.models.scan_preview import PreviewPhase, PreviewTool, PreviewToolStatus
from shared.services.scan_resolve import merge_engine_context
from stages.config import Scale
from stages.registry import ordered_levels, phases


def stage_effects(
    resolved, configured: set[str]
) -> tuple[list[PreviewPhase], list[str]]:
    warnings: list[str] = []
    statuses = _stage_statuses(resolved, configured, warnings)
    out = [
        PreviewPhase(
            phase=phase_name,
            label=phase_name.replace("_", " ").title(),
            tools=[statuses[spec.name] for spec in specs],
        )
        for phase_name, specs in phases()
    ]
    return out, warnings


def _stage_statuses(
    resolved, configured: set[str], warnings: list[str]
) -> dict[str, PreviewTool]:
    """One status per stage, walking levels so a producer only feeds later levels."""
    available = set(seed_produces(resolved.target_type))
    out: dict[str, PreviewTool] = {}
    for level in ordered_levels():
        produced: set[str] = set()
        for spec in level:
            tool = _stage_status(spec, resolved, configured, available, warnings)
            out[spec.name] = tool
            if tool.status is PreviewToolStatus.WILL_RUN:
                produced |= spec.produces
        available |= produced
    return out


def _stage_status(
    spec, resolved, configured: set[str], available: set[str], warnings: list[str]
) -> PreviewTool:
    values = resolved.stage(spec.name)

    def _skip(status: PreviewToolStatus, reason: str) -> PreviewTool:
        return PreviewTool(
            capability=spec.name, label=spec.title, status=status, reason=reason
        )

    if not values.get("enabled", True):
        reason = (
            "Skipped at passive intensity. This stage sends traffic to the target."
            if resolved.intensity == Intensity.PASSIVE.value and spec.touches_target
            else "Disabled in engine."
        )
        return _skip(PreviewToolStatus.SKIPPED_DISABLED, reason)
    if resolved.target_type not in spec.applies_to:
        return _skip(
            PreviewToolStatus.SKIPPED_NOT_APPLICABLE,
            f"Not applicable to {resolved.target_type} targets.",
        )
    if spec.consumes and not (spec.consumes & available):
        kinds = " or ".join(ASSET_KIND_LABELS[k] for k in sorted(spec.consumes))
        reason = f"No earlier stage produces the {kinds} this stage reads."
        warnings.append(f"{spec.title}: {reason}")
        return _skip(PreviewToolStatus.SKIPPED_NO_INPUT, reason)

    missing = [k for k in spec.api_keys if k not in configured]
    if missing and len(missing) == len(spec.api_keys) and spec.requires_api_keys:
        reason = f"{spec.title} skipped. API key not configured."
        warnings.append(reason)
        return _skip(PreviewToolStatus.SKIPPED_NEEDS_KEY, reason)
    if missing:
        warnings.append(
            f"{spec.title}: no API key for {', '.join(missing)}. Reduced coverage."
        )

    scaled = spec.config_model.scaled_fields()

    def _scaled(kind: Scale):
        return next((values[f] for f, (s, _) in scaled.items() if s is kind), None)

    return PreviewTool(
        capability=spec.name,
        label=spec.title,
        status=PreviewToolStatus.WILL_RUN,
        rate=_scaled(Scale.RATE),
        threads=_scaled(Scale.THREADS),
        timeout=_scaled(Scale.TIMEOUT),
    )


class _DraftEngine:
    def __init__(self, data) -> None:
        self.intensity = data.intensity
        self.global_threads = data.global_threads
        self.global_http_crawl = True
        self.global_headers = []
        self.tool_options = {}
        self.stages = _validate_stages(data.stages)


async def preview_engine(
    data, session: AsyncSession | None = None
) -> EnginePreviewResult:
    if data.target_type not in {t.value for t in TargetType}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown target type '{data.target_type}'.",
        )
    _validate_intensity(data.intensity)
    _validate_global_threads(data.global_threads)
    context: object | None = None
    if data.context is not None:
        context = data.context.model_dump()
    elif data.context_id is not None and session is not None:
        context = (
            await session.execute(
                select(ScanContext).where(ScanContext.id == data.context_id)
            )
        ).scalar_one_or_none()
        if context is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scan context not found"
            )
    resolved = merge_engine_context(
        _DraftEngine(data), context, "preview", data.target_type
    )
    phases, warnings = stage_effects(resolved, set())
    return EnginePreviewResult(
        phases=phases,
        resolved_stages=resolved.stages,
        resolved=PreviewResolved(
            header_names=list(resolved.headers),
            global_threads=resolved.global_threads,
            global_rate_limit_ceiling=resolved.global_rate_limit_ceiling,
            per_tool_rate_limits=resolved.per_tool_rate_limits,
            excluded_subdomains=resolved.excluded_subdomains,
            excluded_paths=resolved.excluded_paths,
            excluded_ips=resolved.excluded_ips,
            included_subdomains=resolved.included_subdomains,
            follow_redirects=resolved.follow_redirects,
            http_protocol=resolved.http_protocol,
        ),
        warnings=warnings,
    )
