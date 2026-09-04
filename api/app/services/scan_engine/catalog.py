from shared.definitions.tools import SCAN_TOOLS
from shared.enums.target import TargetType
from shared.models.scan_engine import (
    EngineCatalog,
    EnginePreset,
    StageCatalogEntry,
    StageField,
    ToolOption,
)
from stages.presets import PRESETS, preset_stages
from stages.registry import phases, rate_tools, stages


def _resolve(prop: dict, defs: dict) -> dict:
    """Flatten a $ref/allOf property (an enum field) onto its definition."""
    ref = prop.get("$ref") or next(
        (m.get("$ref") for m in prop.get("allOf") or [] if isinstance(m, dict)), None
    )
    if not ref or not ref.startswith("#/$defs/"):
        return prop
    target = defs.get(ref.rsplit("/", 1)[-1])
    return {**target, **prop} if isinstance(target, dict) else prop


def _field_specs(spec) -> list[StageField]:
    schema = spec.schema
    defs = schema.get("$defs") or {}
    defaults = spec.defaults
    launch = set(spec.launch_fields)
    out: list[StageField] = []
    for name, raw in (schema.get("properties") or {}).items():
        prop = _resolve(raw, defs)
        options = prop.get("enum") or prop.get("options")
        out.append(
            StageField(
                name=name,
                title=prop.get("title") or name.replace("_", " ").capitalize(),
                description=prop.get("description") or None,
                type=_JSON_TYPES.get(prop.get("type"), prop.get("type") or "string"),
                default=defaults.get(name, prop.get("default")),
                options=list(options) if options else None,
                option_labels=prop.get("option_labels") or None,
                minimum=prop.get("minimum"),
                maximum=prop.get("maximum"),
                scale=prop.get("scale"),
                widget=prop.get("widget"),
                launch=name in launch,
            )
        )
    return out


def build_catalog() -> EngineCatalog:
    return EngineCatalog(
        phases=[phase for phase, _ in phases()],
        stages=[
            StageCatalogEntry(
                name=spec.name,
                title=spec.title,
                description=spec.description,
                phase=spec.phase,
                level=spec.level,
                applies_to=sorted(spec.applies_to),
                tools=list(spec.tools),
                api_keys=list(spec.api_keys),
                requires_api_keys=spec.requires_api_keys,
                touches_target=spec.touches_target,
                launch_fields=list(spec.launch_fields),
                defaults=spec.defaults,
                fields=_field_specs(spec),
            )
            for spec in stages()
        ],
        rate_tools=list(rate_tools()),
        tool_options=[ToolOption(**t.model_dump()) for t in SCAN_TOOLS],
        presets=[
            EnginePreset(
                name=p.name,
                title=p.title,
                description=p.description,
                stages=preset_stages(p.name),
            )
            for p in PRESETS
        ],
        target_types=[t.value for t in TargetType],
    )


_JSON_TYPES = {
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "string": "string",
}
