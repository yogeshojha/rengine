import re
import shlex
from collections import defaultdict

import yaml
from fastapi import HTTPException, status
from pydantic import ValidationError

from shared.definitions.tools import MAX_TOOL_OPTION_LEN, TOOL_NAMES, denied_flag
from shared.enums.scan import INTENSITIES
from shared.services.scan_resolve import (
    _CRED_FLAG,
    _HEADER_VALUE,
    _USER_FLAG,
    _VAR_FLAG,
    MASK,
    PROXY_CREDS_RE,
    _reject_ctrl,
    redact_command,
)
from shared.utils.yaml_safe import DocumentTooLargeError, load_document
from stages.registry import stage_by_name, stages

_MAX_HEADERS = 1000
_MAX_HEADER_LEN = 4096
_MAX_YAML_LEN = 512 * 1024
_INTENSITIES = set(INTENSITIES)
_HEADER_NAME = re.compile(r"([\w-]+)\s*:\s*$")
_PROXY_HOST = re.compile(r"[^/\s\"']*")
_SECRET_KEYS = ("tool_options", "global_headers")
_SECRET_KEY_BLOCK = re.compile(
    rf"^[\"']?(?:{'|'.join(_SECRET_KEYS)})[\"']?[ \t]*:[^\n]*"
    r"(?:\n(?:[ \t]+[^\n]*|[ \t]*(?=\n)))*\n?",
    re.MULTILINE,
)
_SECRET_KEY_HINT = re.compile("|".join(_SECRET_KEYS))


def _mask_tool_options(
    options: dict | None, *, superuser: bool = False
) -> dict[str, str]:
    if not superuser:
        return {t: MASK if v else v for t, v in (options or {}).items()}
    return {t: redact_command(v) for t, v in (options or {}).items()}


def _secret_slots(text: str) -> list[tuple[int, int, str]]:
    """Span and owner of each run redact_command masks: a flag, a header or a proxy."""
    slots: dict[int, tuple[int, str]] = {}
    for m in PROXY_CREDS_RE.finditer(text):
        host = _PROXY_HOST.match(text, m.end()).group()
        slots.setdefault(m.end(1), (m.end() - 1, f"proxy {m.group(1)}{host}".lower()))
    for m in _HEADER_VALUE.finditer(text):
        name = _HEADER_NAME.search(m.group(1)).group(1)
        slots.setdefault(m.start(2), (m.end(2), f"header {name}".lower()))
    for m in _VAR_FLAG.finditer(text):
        slots.setdefault(m.start(3), (m.end(3), f"var {m.group(2)}".lower()))
    for m in _USER_FLAG.finditer(text):
        slots.setdefault(m.start(3), (m.end(3), f"user {m.group(2)}".lower()))
    for m in _CRED_FLAG.finditer(text):
        flag = m.group(1).rstrip(" \t=").lstrip("-")
        slots.setdefault(m.start(2), (m.end(2), f"flag {flag}".lower()))
    return sorted((start, end, key) for start, (end, key) in slots.items())


def _unmask_tool_options(submitted: dict | None, stored: dict | None) -> dict[str, str]:
    """Restore each masked run from the stored run of the same flag, header or proxy."""
    stored = stored or {}
    out: dict[str, str] = {}
    for tool, value in (submitted or {}).items():
        if not value or MASK not in value or tool not in stored:
            out[tool] = value
            continue
        if value.strip() == MASK:
            out[tool] = stored[tool]
            continue
        original = stored[tool] or ""
        runs: dict[str, list[str]] = defaultdict(list)
        for start, end, key in _secret_slots(original):
            runs[key].append(original[start:end])
        parts: list[str] = []
        cursor = 0
        for start, end, key in _secret_slots(value):
            if start < cursor or value[start:end] != MASK or not runs[key]:
                continue
            parts += [value[cursor:start], runs[key].pop(0)]
            cursor = end
        out[tool] = "".join([*parts, value[cursor:]])
    return out


def _without_secret_keys(source: str | None) -> str | None:
    """The engine document with no tool_options or global_headers block."""
    if not source or not _SECRET_KEY_HINT.search(source):
        return source
    stripped = _SECRET_KEY_BLOCK.sub("", source)
    try:
        data = load_document(stripped)
    except (yaml.YAMLError, DocumentTooLargeError):
        return None
    if isinstance(data, dict) and any(key in data for key in _SECRET_KEYS):
        return None
    return stripped


def _validate_yaml_source(source: str | None) -> str | None:
    if source is None:
        return None
    if len(source) > _MAX_YAML_LEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Engine YAML may not exceed {_MAX_YAML_LEN} characters.",
        )
    try:
        load_document(source)
    except DocumentTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid YAML: {exc}"
        ) from exc
    return _without_secret_keys(source)


def _validate_tool_options(options: dict | None) -> dict[str, str]:
    """Keep only known tools."""
    clean: dict[str, str] = {}
    for tool, raw in (options or {}).items():
        if tool not in TOOL_NAMES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"'{tool}' does not take custom arguments. "
                    f"Tools that do: {', '.join(sorted(TOOL_NAMES))}."
                ),
            )
        value = (raw or "").strip()
        if not value:
            continue
        if len(value) > MAX_TOOL_OPTION_LEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{tool} options may not exceed {MAX_TOOL_OPTION_LEN} characters.",
            )
        if MASK in value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{tool} options carry a masked value. Enter the value again.",
            )
        _reject_ctrl(f"{tool} options", value)
        try:
            tokens = shlex.split(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{tool} options are not valid shell arguments: {exc}",
            ) from exc
        flag = denied_flag(tool, tokens)
        if flag:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{tool} does not take {flag}.",
            )
        clean[tool] = value
    return clean


def _check_tool_options_access(
    superuser: bool, stored: dict | None, submitted: dict | None
) -> None:
    if superuser or dict(stored or {}) == dict(submitted or {}):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Tool arguments require administrator access.",
    )


def _validate_intensity(intensity: str | None) -> None:
    if intensity is not None and intensity not in _INTENSITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Intensity must be one of {', '.join(INTENSITIES)}.",
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
        if MASK in line:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"The header '{line.split(':', 1)[0].strip()}' carries a masked "
                    "value. Enter the value again."
                ),
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
            if value.strip():
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
            if MASK in value and name.strip().lower() in stored_map:
                out.append(f"{name.strip()}: {stored_map[name.strip().lower()]}")
                continue
        out.append(line)
    return out


def _validate_stages(submitted: dict | None) -> dict[str, dict]:
    known = stage_by_name()
    clean: dict[str, dict] = {}
    for name, authored in (submitted or {}).items():
        spec = known.get(name)
        raw = authored
        if spec is not None and spec.catalog_hidden:
            continue
        if spec is not None and spec.always_on and isinstance(raw, dict):
            raw = {k: v for k, v in raw.items() if k != "enabled"}
            if not raw:
                continue
        if spec is None:
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
        spec.name: spec.config_model(**(stored.get(spec.name) or {})).model_dump(
            mode="json"
        )
        for spec in stages()
        if not spec.catalog_hidden
    }
