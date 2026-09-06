import re
import shlex

import yaml
from fastapi import HTTPException, status
from pydantic import ValidationError

from shared.definitions.tools import MAX_TOOL_OPTION_LEN, TOOL_NAMES
from shared.enums.scan import INTENSITIES
from shared.services.scan_resolve import (
    _SENSITIVE_HEADER,
    MASK,
    _reject_ctrl,
    redact_command,
)
from stages.registry import stage_by_name, stages

_MAX_HEADERS = 1000
_MAX_HEADER_LEN = 4096
_MAX_YAML_LEN = 512 * 1024
_INTENSITIES = set(INTENSITIES)
_MAX_ENGINE_THREADS = 1000
_MASKED_RUN = re.compile(
    r"(?:-{1,2}(?:api[-_]?key|key|token|password|passwd|pass|secret)[ =])(\S+)",
    re.IGNORECASE,
)


def _mask_tool_options(options: dict | None) -> dict[str, str]:
    return {t: redact_command(v) for t, v in (options or {}).items()}


def _unmask_tool_options(submitted: dict | None, stored: dict | None) -> dict[str, str]:
    """Restore each masked run in place, so edits made alongside a secret survive."""
    stored = stored or {}
    out: dict[str, str] = {}
    for tool, value in (submitted or {}).items():
        if not value or MASK not in value or tool not in stored:
            out[tool] = value
            continue
        secrets = _MASKED_RUN.findall(redact_command(stored[tool]) or "")
        originals = _MASKED_RUN.findall(stored[tool])
        restored = value
        if len(secrets) == len(originals):
            for original in originals:
                restored = restored.replace(MASK, original, 1)
        else:
            restored = stored[tool]
        out[tool] = restored
    return out


_MAX_HEADERS = 1000
_MAX_HEADER_LEN = 4096
_MAX_YAML_LEN = 512 * 1024
_MASKED_RUN = re.compile(
    r"(?:-{1,2}(?:api[-_]?key|key|token|password|passwd|pass|secret)[ =])(\S+)",
    re.IGNORECASE,
)


def _validate_yaml_source(source: str | None) -> str | None:
    if source is None:
        return None
    if len(source) > _MAX_YAML_LEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stage YAML may not exceed {_MAX_YAML_LEN} bytes.",
        )
    try:
        yaml.safe_load(source)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid YAML: {exc}"
        ) from exc
    return source


_INTENSITIES = set(INTENSITIES)
_MAX_ENGINE_THREADS = 1000


def _validate_tool_options(options: dict | None) -> dict[str, str]:
    """Keep only known tools; reject over-long or unparseable arg strings."""
    clean: dict[str, str] = {}
    for tool, raw in (options or {}).items():
        if tool not in TOOL_NAMES:
            continue
        value = (raw or "").strip()
        if not value:
            continue
        if len(value) > MAX_TOOL_OPTION_LEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{tool} options may not exceed {MAX_TOOL_OPTION_LEN} characters.",
            )
        _reject_ctrl(f"{tool} options", value)
        try:
            shlex.split(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{tool} options are not valid shell arguments: {exc}",
            ) from exc
        clean[tool] = value
    return clean


def _validate_intensity(intensity: str | None) -> None:
    if intensity is not None and intensity not in _INTENSITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"intensity must be one of {sorted(_INTENSITIES)}.",
        )


def _validate_global_threads(threads: int | None) -> None:
    if threads is not None and not (1 <= threads <= _MAX_ENGINE_THREADS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"global_threads must be between 1 and {_MAX_ENGINE_THREADS}.",
        )


def _validate_global_headers(headers: list) -> None:
    if headers and len(headers) > _MAX_HEADERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"global_headers may not exceed {_MAX_HEADERS} entries.",
        )
    for line in headers or []:
        if isinstance(line, str) and len(line) > _MAX_HEADER_LEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Each global header may not exceed {_MAX_HEADER_LEN} characters.",
            )
        if not isinstance(line, str) or ":" not in line:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each global header must be a 'Name: Value' string.",
            )
        name, value = line.split(":", 1)
        if not name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each global header must have a non-empty name.",
            )
        _reject_ctrl("Header name", name)
        _reject_ctrl("Header value", value)


def _mask_global_headers(headers: list) -> list[str]:
    out: list[str] = []
    for line in headers or []:
        if isinstance(line, str) and ":" in line:
            name, value = line.split(":", 1)
            if value.strip() and _SENSITIVE_HEADER.search(name.strip()):
                out.append(f"{name.strip()}: {MASK}")
                continue
        out.append(line)
    return out


def _unmask_global_headers(incoming: list, stored: list) -> list[str]:
    stored_map: dict[str, str] = {}
    for line in stored or []:
        if isinstance(line, str) and ":" in line:
            name, value = line.split(":", 1)
            stored_map[name.strip().lower()] = value.strip()
    out: list[str] = []
    for line in incoming or []:
        if isinstance(line, str) and ":" in line:
            name, value = line.split(":", 1)
            if value.strip() == MASK and name.strip().lower() in stored_map:
                out.append(f"{name.strip()}: {stored_map[name.strip().lower()]}")
                continue
        out.append(line)
    return out


def _validate_stages(submitted: dict | None) -> dict[str, dict]:
    known = stage_by_name()
    clean: dict[str, dict] = {}
    for name, raw in (submitted or {}).items():
        spec = known.get(name)
        if spec is None or spec.catalog_hidden:
            offered = sorted(n for n, s in known.items() if not s.catalog_hidden)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown stage '{name}'. Known stages: {', '.join(offered)}.",
            )
        if not isinstance(raw, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stage '{name}' config must be an object.",
            )
        known_fields = set(spec.config_model.model_fields)
        unknown = [k for k in raw if k not in known_fields]
        if unknown:
            hint = ", ".join(sorted(known_fields))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Stage '{name}' has no setting {', '.join(repr(u) for u in unknown)}. "
                    f"Valid settings: {hint}."
                ),
            )
        try:
            # validate against the whole model, but persist only the submitted keys
            validated = spec.config_model(**raw).model_dump()
            clean[name] = {k: validated[k] for k in raw if k in validated}
        except ValidationError as exc:
            problems = "; ".join(
                f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}"
                for e in exc.errors()
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid config for stage '{name}': {problems}",
            ) from exc
    return clean


def _full_stages(stored: dict | None) -> dict[str, dict]:
    stored = stored or {}
    return {
        spec.name: spec.config_model(**(stored.get(spec.name) or {})).model_dump()
        for spec in stages()
    }


_JSON_TYPES = {
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "string": "string",
}
