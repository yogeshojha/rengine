from __future__ import annotations

import base64
import re
from collections.abc import Iterable
from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, Field, PrivateAttr

from shared.definitions.constants import MAX_RATE, MAX_THREADS, MAX_TIMEOUT
from shared.definitions.tools import parse_tool_args

if TYPE_CHECKING:
    from fastapi import HTTPException

MASK = "••••••••"

SECRET_FIELDS = {
    "bearer_token",
    "basic_password",
    "header_value",
    "cookie_value",
    "api_key_value",
}

_SENSITIVE_HEADER = re.compile(
    r"^(authorization|cookie|x-api-key)$|token|secret", re.IGNORECASE
)

PROXY_CREDS_RE = re.compile(r"(\w+://)[^/\s]*@")
_HEADER_VALUE = re.compile(
    r'(-H\s+["\']?(?:authorization|cookie|x-api-key|[\w-]*(?:token|secret)[\w-]*)'
    r'\s*:\s*)([^"\'\n]+?)(?=["\']|\s+-|\s*$)',
    re.IGNORECASE,
)
_CRED_FLAG = re.compile(
    r"((?:-{1,2}(?:api[-_]?key|key|token|password|passwd|pass|secret))[ =])(\S+)",
    re.IGNORECASE,
)
_UNSAFE_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_CTRL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def _bad(detail: str) -> HTTPException:
    from fastapi import HTTPException, status  # noqa: PLC0415

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _reject_ctrl(label: str, value) -> None:
    if isinstance(value, str) and _CTRL_CHARS.search(value):
        msg = f"{label} must not contain control characters (CR/LF/NUL)."
        raise _bad(msg)


def _mask_auth(auth: dict) -> dict:
    masked = dict(auth or {})
    for field in SECRET_FIELDS:
        if masked.get(field):
            masked[field] = MASK
    return masked


def _mask_headers(headers: list) -> list:
    out = []
    for h in headers or []:
        name = h.get("name", "")
        value = h.get("value", "")
        if value and _SENSITIVE_HEADER.search(name):
            value = MASK
        out.append({"name": name, "value": value})
    return out


def mask_proxy_url(value: str | None) -> str | None:
    return PROXY_CREDS_RE.sub(rf"\1{MASK}@", value) if value else value


def redact_command(command: str) -> str:
    """Strip NUL/control bytes + proxy creds + sensitive header/flag values for safe storage."""
    safe = _UNSAFE_CTRL.sub("", command or "")
    safe = PROXY_CREDS_RE.sub(rf"\1{MASK}@", safe)
    safe = _HEADER_VALUE.sub(rf"\1{MASK}", safe)
    return _CRED_FLAG.sub(rf"\1{MASK}", safe)


MIN_SECRET_LENGTH = 8


def redact_secrets(text: str | None, secrets: Iterable[str]) -> str | None:
    """Mask credential values the scan itself injected, wherever a tool echoed them back.

    Stored proof (a raw request, a curl command) carries whatever headers the scan
    context supplied. nuclei masks the header names it knows; a custom one is its own
    business, so we mask by value instead of by name.
    """
    if not text:
        return text
    for secret in secrets:
        if secret and len(secret) >= MIN_SECRET_LENGTH:
            text = text.replace(secret, MASK)
    return text


def _auth_summary(auth: dict, extra_headers: list) -> str:  # noqa: PLR0911
    auth = auth or {}
    auth_type = auth.get("auth_type", "none")
    if auth_type == "bearer":
        return "Bearer ••••"
    if auth_type == "basic":
        user = auth.get("basic_username") or ""
        return f"Basic ({user})" if user else "Basic"
    if auth_type == "cookie":
        return "Cookie ••••"
    if auth_type == "header":
        return auth.get("header_name") or "Header"
    if auth_type == "api_key":
        return auth.get("api_key_name") or "API Key"
    n = len(extra_headers or [])
    if n:
        return f"{n} header{'s' if n != 1 else ''}"
    return "None"


def resolve_headers(ctx_or_auth, extra_headers: list | None = None) -> dict[str, str]:
    def _get(key: str):
        if isinstance(ctx_or_auth, dict):
            return ctx_or_auth.get(key)
        return getattr(ctx_or_auth, key, None)

    auth_type = _get("auth_type") or "none"
    headers: dict[str, str] = {}

    if auth_type == "bearer":
        token = _get("bearer_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_type == "basic":
        user = _get("basic_username") or ""
        password = _get("basic_password") or ""
        raw = f"{user}:{password}".encode()
        headers["Authorization"] = "Basic " + base64.b64encode(raw).decode()
    elif auth_type == "header":
        name = _get("header_name")
        value = _get("header_value")
        if name:
            headers[name] = value or ""
    elif auth_type == "cookie":
        cookie = _get("cookie_value")
        if cookie:
            headers["Cookie"] = cookie
    elif auth_type == "api_key":
        name = _get("api_key_name")
        value = _get("api_key_value")
        if name:
            headers[name] = value or ""

    lower_map = {k.lower(): k for k in headers}
    for h in extra_headers or []:
        if isinstance(h, dict):
            name = h.get("name")
            value = h.get("value", "")
        else:
            name = getattr(h, "name", None)
            value = getattr(h, "value", "")
        if not name:
            continue
        existing = lower_map.get(name.lower())
        if existing is not None:
            del headers[existing]
        headers[name] = value
        lower_map[name.lower()] = name

    return headers


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


class _NeutralContext:
    auth: ClassVar[dict] = {"auth_type": "none"}
    extra_headers: ClassVar[list] = []
    global_rate_limit_override = None
    per_tool_rate_overrides: ClassVar[dict] = {}
    thread_multiplier = 1.0
    timeout_multiplier = 1.0
    excluded_subdomains: ClassVar[list] = []
    excluded_paths: ClassVar[list] = []
    excluded_ips: ClassVar[list] = []
    included_subdomains: ClassVar[list] = []
    follow_redirects_override = None
    http_protocol = "both"
    compare_baseline_scan_id = None
    scan_only_new_assets = False


class ResolvedScanConfig(BaseModel):
    target_value: str
    target_type: str
    headers: dict[str, str] = Field(default_factory=dict)
    per_tool_rate_limits: dict[str, int] = Field(default_factory=dict)
    global_rate_limit_ceiling: int | None = None
    global_threads: int = 30
    thread_multiplier: float = 1.0
    timeout_multiplier: float = 1.0
    stages: dict[str, dict] = Field(default_factory=dict)
    excluded_subdomains: list[str] = Field(default_factory=list)
    excluded_paths: list[str] = Field(default_factory=list)
    excluded_ips: list[str] = Field(default_factory=list)
    included_subdomains: list[str] = Field(default_factory=list)
    follow_redirects: bool | None = None
    http_protocol: str = "both"
    global_http_crawl: bool = True
    intensity: str = "normal"
    proxy_url: str | None = None
    tool_options: dict[str, str] = Field(default_factory=dict)
    overrides: dict[str, dict] = Field(default_factory=dict)

    _auth_header_names: list[str] = PrivateAttr(default_factory=list)

    def tool_args(self, tool: str) -> list[str]:
        return parse_tool_args((self.tool_options or {}).get(tool, ""))

    def stage(self, name: str) -> dict:
        return self.stages.get(name) or {}

    def __repr__(self) -> str:
        proxy = "<set>" if self.proxy_url else "None"
        return (
            f"ResolvedScanConfig(target_value={self.target_value!r}, "
            f"target_type={self.target_type!r}, "
            f"headers=<{len(self.headers)} redacted>, "
            f"global_threads={self.global_threads}, "
            f"http_protocol={self.http_protocol!r}, intensity={self.intensity!r}, "
            f"proxy={proxy})"
        )

    __str__ = __repr__


def _check_baseline_deferred(compare_baseline_scan_id, scan_only_new_assets) -> None:
    if compare_baseline_scan_id is not None or scan_only_new_assets:
        from fastapi import HTTPException, status  # noqa: PLC0415

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Baseline comparison is not available yet.",
        )


def _ctx_get(ctx, key, default=None):
    if isinstance(ctx, dict):
        return ctx.get(key, default)
    return getattr(ctx, key, default)


def _build_headers(engine, ctx) -> tuple[dict[str, str], list[str]]:
    headers: dict[str, str] = {}
    for line in engine.global_headers or []:
        if not isinstance(line, str) or ":" not in line:
            continue
        name, value = line.split(":", 1)
        name = name.strip()
        value = value.strip()
        if name:
            headers[name] = value

    auth = _ctx_get(ctx, "auth") or {"auth_type": "none"}
    extra_headers = _ctx_get(ctx, "extra_headers") or []
    ctx_headers = resolve_headers(auth, extra_headers)

    auth_header_names: list[str] = list(ctx_headers.keys())

    lower_map = {k.lower(): k for k in headers}
    for name, value in ctx_headers.items():
        existing = lower_map.get(name.lower())
        if existing is not None:
            del headers[existing]
        headers[name] = value
        lower_map[name.lower()] = name

    for k, v in headers.items():
        _reject_ctrl("Header name", k)
        _reject_ctrl("Header value", v)

    return headers, auth_header_names


def _resolve_rate(
    base: int, tool: str | None, overrides: dict, ceiling: int | None
) -> int:
    value = overrides.get(tool, base) if tool else base
    if ceiling is not None:
        value = min(value, ceiling)
    return _clamp(int(value), 1, MAX_RATE)


def _assert_flags_preserved(stage: str, original: dict, scaled: dict) -> None:
    for key, value in original.items():
        if isinstance(value, bool) and scaled[key] != value:
            msg = f"Resolved enable flag {stage}.{key} diverged from engine."
            raise RuntimeError(msg)


def validate_overrides(overrides: dict | None) -> dict[str, dict]:
    """Keep only stage keys that exist and values their own config model accepts."""
    from stages.registry import stage_by_name  # noqa: PLC0415

    if not overrides:
        return {}
    specs = stage_by_name()
    clean: dict[str, dict] = {}
    for name, values in overrides.items():
        spec = specs.get(name)
        if spec is None or not isinstance(values, dict):
            msg = f"Unknown stage {name!r} in run overrides."
            raise _bad(msg)
        allowed = set(spec.config_model.model_fields)
        unknown = sorted(set(values) - allowed)
        if unknown:
            msg = f"{name} has no setting named {unknown[0]!r}."
            raise _bad(msg)
        try:
            spec.config_model(**{**spec.defaults, **values})
        except Exception as exc:
            msg = f"{name}: {str(exc).splitlines()[0][:200]}"
            raise _bad(msg) from exc
        clean[name] = dict(values)
    return clean


def merge_engine_context(
    engine,
    context,
    target_value: str,
    target_type: str,
    proxy_url: str | None = None,
    overrides: dict | None = None,
) -> ResolvedScanConfig:
    from shared.enums.scan import Intensity  # noqa: PLC0415
    from stages.config import Scale  # noqa: PLC0415
    from stages.registry import stages as stage_specs  # noqa: PLC0415

    passive = engine.intensity == Intensity.PASSIVE.value

    ctx = context if context is not None else _NeutralContext()

    _check_baseline_deferred(
        _ctx_get(ctx, "compare_baseline_scan_id"),
        _ctx_get(ctx, "scan_only_new_assets"),
    )

    thread_mult = float(_ctx_get(ctx, "thread_multiplier", 1.0))
    timeout_mult = float(_ctx_get(ctx, "timeout_multiplier", 1.0))
    rate_overrides = _ctx_get(ctx, "per_tool_rate_overrides") or {}
    global_rate_limit_ceiling = _ctx_get(ctx, "global_rate_limit_override")

    headers, auth_header_names = _build_headers(engine, ctx)
    global_threads = _clamp(round(engine.global_threads * thread_mult), 1, MAX_THREADS)

    stored = engine.stages or {}
    run_overrides = validate_overrides(overrides)
    stages: dict[str, dict] = {}
    per_tool_rate_limits: dict[str, int] = {}

    for spec in stage_specs():
        config = spec.config_model(
            **{**(stored.get(spec.name) or {}), **(run_overrides.get(spec.name) or {})}
        )
        values = config.model_dump()
        for name, (scale, tool) in spec.config_model.scaled_fields().items():
            base = values[name]
            if scale is Scale.THREADS:
                values[name] = _clamp(int(base * thread_mult) or 1, 1, MAX_THREADS)
            elif scale is Scale.TIMEOUT:
                values[name] = _clamp(int(base * timeout_mult) or 1, 1, MAX_TIMEOUT)
            elif scale is Scale.RATE:
                values[name] = _resolve_rate(
                    base, tool, rate_overrides, global_rate_limit_ceiling
                )
                per_tool_rate_limits[tool] = values[name]
        _assert_flags_preserved(spec.name, config.model_dump(), values)
        if passive and spec.touches_target:
            values["enabled"] = False
        stages[spec.name] = values

    excluded_subdomains = list(_ctx_get(ctx, "excluded_subdomains") or [])
    excluded_paths = list(_ctx_get(ctx, "excluded_paths") or [])
    excluded_ips = list(_ctx_get(ctx, "excluded_ips") or [])
    included_subdomains = list(_ctx_get(ctx, "included_subdomains") or [])

    follow_redirects_override = _ctx_get(ctx, "follow_redirects_override")
    follow_redirects = (
        follow_redirects_override if follow_redirects_override is not None else None
    )
    http_protocol = _ctx_get(ctx, "http_protocol", "both") or "both"

    config = ResolvedScanConfig(
        target_value=target_value,
        target_type=target_type,
        headers=headers,
        per_tool_rate_limits=per_tool_rate_limits,
        global_rate_limit_ceiling=global_rate_limit_ceiling,
        global_threads=global_threads,
        thread_multiplier=thread_mult,
        timeout_multiplier=timeout_mult,
        stages=stages,
        excluded_subdomains=excluded_subdomains,
        excluded_paths=excluded_paths,
        excluded_ips=excluded_ips,
        included_subdomains=included_subdomains,
        follow_redirects=follow_redirects,
        http_protocol=http_protocol,
        global_http_crawl=engine.global_http_crawl,
        intensity=engine.intensity,
        tool_options=dict(getattr(engine, "tool_options", None) or {}),
        overrides=run_overrides,
    )
    config._auth_header_names = auth_header_names
    config.proxy_url = proxy_url
    return config
