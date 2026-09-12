"""Stage overrides for a focused run."""

from __future__ import annotations

from shared.enums.scan import Phase, StageRole

_DISCOVERY = Phase.DISCOVERY.value


def focused_overrides(picked: list[str] | tuple[str, ...]) -> dict:
    """Disable every stage that enumerates the target."""
    from stages.registry import stage_by_name  # noqa: PLC0415

    known = stage_by_name()
    overrides = {
        name: {"enabled": False}
        for name, spec in known.items()
        if not spec.catalog_hidden
        and (
            spec.role == StageRole.CAPABILITY.value
            or (not spec.consumes and (spec.produces or spec.phase == _DISCOVERY))
        )
    }
    for name in picked:
        overrides[name] = {**(overrides.get(name) or {}), "enabled": True}
    return overrides
