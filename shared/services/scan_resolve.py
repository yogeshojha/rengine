from __future__ import annotations

import base64
import contextlib
import re
from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import unquote, urlsplit

from pydantic import BaseModel, Field, PrivateAttr, ValidationError

from shared.definitions.constants import MAX_RATE
from shared.definitions.intensity import tool_rate
from shared.definitions.tools import denied_flag, parse_tool_args
from shared.enums.scan_context import AuthType, HttpProtocol
from shared.utils.net import redact_url_queries

if TYPE_CHECKING:
    from fastapi import HTTPException

MASK = "••••••••"
MASK_TAIL = 4


def mask_tail(value: str) -> str:
    """MASK and the last four characters when the value has more than eight."""
    return f"{MASK}{value[-MASK_TAIL:]}" if len(value) > MASK_TAIL * 2 else MASK


SECRET_FIELDS = {
    "bearer_token",
    "basic_password",
    "header_value",
    "cookie_value",
    "api_key_value",
}

_CREDENTIAL_NAME = (
    r"(?:authorization|proxy-authorization|x-authorization|authentication"
    r"|cookie|set-cookie|x-csrf-token|x-auth[^\s:\"']*+|[^\s:\"']*-auth"
    r"|(?!access-control-)(?=[^\s:\"']*(?:token|secret|key|session|passw"
    r"|credential|signature|jwt|assertion))[^\s:\"']*+)"
)
CREDENTIAL_HEADER = re.compile(rf"^{_CREDENTIAL_NAME}$", re.IGNORECASE)

PROXY_CREDS_RE = re.compile(r"(\w+://)([^/\s]*)@")

_HEADER_FLAG = r"-{1,2}(?:headers|header|H)(?:\s+|=)"
_HEADER_VALUE = re.compile(
    rf'({_HEADER_FLAG}["\']?[\w-]+\s*:\s*)([^"\'\n]+?)'
    r'(?=["\']|\s+-{1,2}[A-Za-z]|\s*$)',
    re.IGNORECASE,
)
_CRED_FLAG = re.compile(
    r"((?:-{1,2}[\w-]*?(?:api[-_]?key|key|token|password|passwd|pass|secret|cookie"
    r"|auth)|(?<![\w-])-b)(?:[ \t]+|=))(\"[^\"]*\"|'[^']*'|\S+)",
    re.IGNORECASE,
)
_VAR_FLAG = re.compile(
    r"((?<![\w-])-{1,2}var(?:[ \t]+|=)[\"']?([\w.-]+)=)([^\s\"']+)",
    re.IGNORECASE,
)
_USER_FLAG = re.compile(
    r"((?<![\w-])-{1,2}(?:u|user|proxy-user)(?:[ \t]+|=)[\"']?([^\s:/\"'@\[]+):)"
    r"(?!//)(?!\d+(?:[\s\"'/,]|$))([^\s\"'@]+)",
    re.IGNORECASE,
)
_UNSAFE_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_CTRL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def _bad(detail: str) -> HTTPException:
    from fastapi import HTTPException, status  # noqa: PLC0415

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _reject_ctrl(label: str, value) -> None:
    if isinstance(value, str) and _CTRL_CHARS.search(value):
        msg = f"{label} must not contain control characters."
        raise _bad(msg)


def _mask_auth(auth: dict) -> dict:
    masked = dict(auth or {})
    for field in SECRET_FIELDS:
        if masked.get(field):
            masked[field] = MASK
    return masked


def _mask_headers(headers: list) -> list:
    return [
        {
            "name": h.get("name", ""),
            "value": MASK if h.get("value") else h.get("value", ""),
        }
        for h in headers or []
    ]


def restore_masked_headers(
    incoming: list[dict], stored: list[dict] | None
) -> list[dict]:
    """Put the stored value back behind every header sent with a masked value."""
    kept = {(h.get("name") or "").strip().lower(): h.get("value") for h in stored or []}
    out: list[dict] = []
    for h in incoming:
        name = (h.get("name") or "").strip()
        if MASK not in (h.get("value") or ""):
            out.append(h)
            continue
        if kept.get(name.lower()) is None:
            msg = f"The header '{name}' carries a masked value. Enter the value again."
            raise _bad(msg)
        out.append({**h, "value": kept[name.lower()]})
    return out


def mask_proxy_url(value: str | None) -> str | None:
    return PROXY_CREDS_RE.sub(rf"\1{MASK}@", value) if value else value


def redact_command(command: str) -> str:
    """Mask proxy credentials and credential flag and header values."""
    safe = _UNSAFE_CTRL.sub("", command or "")
    safe = PROXY_CREDS_RE.sub(rf"\1{MASK}@", safe)
    safe = _HEADER_VALUE.sub(rf"\1{MASK}", safe)
    safe = _VAR_FLAG.sub(rf"\1{MASK}", safe)
    safe = _USER_FLAG.sub(rf"\1{MASK}", safe)
    return _CRED_FLAG.sub(rf"\1{MASK}", safe)


def command_secrets(command: str) -> list[str]:
    """The values redact_command masks in a command line."""
    found = [m.group(2) for m in PROXY_CREDS_RE.finditer(command or "")]
    for pattern in (_HEADER_VALUE, _CRED_FLAG):
        found += [m.group(2).strip("\"'") for m in pattern.finditer(command or "")]
    for pattern in (_VAR_FLAG, _USER_FLAG):
        found += [m.group(3) for m in pattern.finditer(command or "")]
    return found


def seal_headers(headers: dict[str, str] | None) -> dict[str, str]:
    """Encrypt header values before they are persisted with a scan."""
    from shared.utils.crypto import encrypt_secret  # noqa: PLC0415

    return {
        name: encrypt_secret(value or "") for name, value in (headers or {}).items()
    }


def unseal_headers(headers: dict[str, str] | None) -> dict[str, str]:
    """Decrypt sealed header values."""
    from shared.utils.crypto import decrypt_stored  # noqa: PLC0415

    out: dict[str, str] = {}
    for name, value in (headers or {}).items():
        out[name] = (
            decrypt_stored(value, label=f"The {name} header on this run")
            if value
            else ""
        )
    return out


_SEALED = re.compile(r"gAAAAA[\w-]+=*")


def is_sealed(value) -> bool:
    return isinstance(value, str) and _SEALED.fullmatch(value) is not None


def seal_run_config(config: dict) -> dict:
    """Encrypt the header values, proxy and tool arguments a run is stored with."""
    from shared.utils.crypto import encrypt_secret  # noqa: PLC0415

    config["headers"] = seal_headers(config.get("headers"))
    if config.get("proxy_url"):
        config["proxy_url"] = encrypt_secret(config["proxy_url"])
    config["tool_options"] = {
        tool: encrypt_secret(value) if value else ""
        for tool, value in (config.get("tool_options") or {}).items()
    }
    return config


def unseal_run_config(config: dict) -> dict:
    """Decrypt what seal_run_config encrypted."""
    from shared.utils.crypto import decrypt_stored  # noqa: PLC0415

    config["headers"] = unseal_headers(config.get("headers"))
    if is_sealed(config.get("proxy_url")):
        config["proxy_url"] = decrypt_stored(
            config["proxy_url"], label="The proxy on this run"
        )
    config["tool_options"] = {
        tool: (
            decrypt_stored(value, label=f"The {tool} command line on this run")
            if is_sealed(value)
            else value
        )
        for tool, value in (config.get("tool_options") or {}).items()
    }
    return config


MIN_SECRET_LENGTH = 8


def redact_secrets(text: str | None, secrets: Iterable[str]) -> str | None:
    """Mask the scan's own credential values."""
    if not text:
        return text
    for secret in secrets:
        if secret and len(secret) >= MIN_SECRET_LENGTH:
            text = text.replace(secret, MASK)
    return text


def redact_recorded(text: str | None, secrets: Iterable[str] = ()) -> str:
    """Mask credential flags and header values, then the caller's own secrets."""
    return redact_secrets(redact_command(text or ""), secrets) or ""


def run_secrets(config: ResolvedScanConfig) -> list[str]:
    """Every credential value a run carries, longest first."""
    found: list[str] = []
    for value in (config.headers or {}).values():
        credential = (value or "").strip().partition(" ")[2].strip()
        found += [value or "", "" if " " in credential else credential]
    if config.proxy_url:
        parts = urlsplit(config.proxy_url)
        password = parts.password or ""
        found += [
            password,
            unquote(password),
            f"{unquote(parts.username or '')}:{unquote(password)}",
            *command_secrets(config.proxy_url),
        ]
    for args in (config.tool_options or {}).values():
        found += command_secrets(args or "")
    unique = {value for value in found if len(value) >= MIN_SECRET_LENGTH}
    return sorted(unique, key=len, reverse=True)


_QUOTED_CREDENTIAL = re.compile(
    rf"""((["']){_CREDENTIAL_NAME}\2\s*[:=]\s*)(["'])(.*?)\3""", re.IGNORECASE
)


def scrub_error(text: str | None, secrets: Iterable[str] = ()) -> str | None:
    """Mask URL queries, credential flags, headers and values, then the run's secrets."""
    if not text:
        return text
    safe = redact_url_queries(redact_command(text))
    safe = _QUOTED_CREDENTIAL.sub(rf"\1\3{MASK}\3", safe)
    safe = _ERROR_HEADER.sub(_masked_header, safe)
    return redact_secrets(safe, secrets)


_held: tuple[tuple[str, ...], tuple[str, ...]] = ((), ())


@contextlib.contextmanager
def holding_secrets(config: ResolvedScanConfig | None) -> Iterator[None]:
    """Bind one run's header names and secrets. A prefork child runs one task at a time."""
    global _held  # noqa: PLW0603
    previous = _held
    if config is not None:
        _held = (tuple(config.headers or {}), tuple(run_secrets(config)))
    try:
        yield
    finally:
        _held = previous


def held_secrets(extra: Iterable[str] = ()) -> list[str]:
    """The bound run's secrets plus extra values, longest first."""
    values = {*_held[1], *(v for v in extra if v and len(v) >= MIN_SECRET_LENGTH)}
    return sorted(values, key=len, reverse=True)


def redact_sent(text: str | None) -> str | None:
    """Mask a request the bound run sent: its headers by name, its secrets, credentials."""
    names, secrets = _held
    return redact_message(redact_secrets(mask_header_values(text, names), secrets))


def _auth_summary(auth: dict, extra_headers: list) -> str:  # noqa: PLR0911
    auth = auth or {}
    auth_type = auth.get("auth_type", AuthType.NONE.value)
    if auth_type == AuthType.BEARER.value:
        return "Bearer ••••"
    if auth_type == AuthType.BASIC.value:
        user = auth.get("basic_username") or ""
        return f"Basic · {user}" if user else "Basic"
    if auth_type == AuthType.COOKIE.value:
        return "Cookie ••••"
    if auth_type == AuthType.HEADER.value:
        return auth.get("header_name") or "Header"
    if auth_type == AuthType.API_KEY.value:
        return auth.get("api_key_name") or "API key"
    n = len(extra_headers or [])
    if n:
        return f"{n} header{'s' if n != 1 else ''}"
    return "None"


def resolve_headers(ctx_or_auth, extra_headers: list | None = None) -> dict[str, str]:
    def _get(key: str):
        if isinstance(ctx_or_auth, dict):
            return ctx_or_auth.get(key)
        return getattr(ctx_or_auth, key, None)

    auth_type = _get("auth_type") or AuthType.NONE.value
    headers: dict[str, str] = {}

    if auth_type == AuthType.BEARER.value:
        token = _get("bearer_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_type == AuthType.BASIC.value:
        user = _get("basic_username") or ""
        password = _get("basic_password") or ""
        if user or password:
            raw = f"{user}:{password}".encode()
            headers["Authorization"] = "Basic " + base64.b64encode(raw).decode()
    elif auth_type == AuthType.HEADER.value:
        name = _get("header_name")
        value = _get("header_value")
        if name:
            headers[name] = value or ""
    elif auth_type == AuthType.COOKIE.value:
        cookie = _get("cookie_value")
        if cookie:
            headers["Cookie"] = cookie
    elif auth_type == AuthType.API_KEY.value:
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
    auth: ClassVar[dict] = {"auth_type": AuthType.NONE.value}
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
    http_protocol = HttpProtocol.BOTH.value


class ResolvedScanConfig(BaseModel):
    target_value: str
    target_type: str
    headers: dict[str, str] = Field(default_factory=dict)
    per_tool_rate_limits: dict[str, int] = Field(default_factory=dict)
    global_rate_limit_ceiling: int | None = None
    thread_multiplier: float = 1.0
    timeout_multiplier: float = 1.0
    stages: dict[str, dict] = Field(default_factory=dict)
    transports: dict[str, dict] = Field(default_factory=dict)
    excluded_subdomains: list[str] = Field(default_factory=list)
    excluded_paths: list[str] = Field(default_factory=list)
    excluded_ips: list[str] = Field(default_factory=list)
    included_subdomains: list[str] = Field(default_factory=list)
    follow_redirects: bool | None = None
    http_protocol: str = HttpProtocol.BOTH.value
    intensity: str = "normal"
    proxy_url: str | None = None
    tool_options: dict[str, str] = Field(default_factory=dict)
    overrides: dict[str, dict] = Field(default_factory=dict)
    seed_assets: list[dict] = Field(default_factory=list)
    seed_only: bool = False

    _auth_header_names: list[str] = PrivateAttr(default_factory=list)

    def tool_args(self, tool: str) -> list[str]:
        args = parse_tool_args((self.tool_options or {}).get(tool, ""))
        return [] if denied_flag(tool, args) else args

    def stage(self, name: str) -> dict:
        return self.stages.get(name) or {}

    def auth_headers(self) -> dict[str, str]:
        names = {n.lower() for n in self._auth_header_names}
        return {k: v for k, v in self.headers.items() if k.lower() in names}

    def headers_without_auth(self) -> dict[str, str]:
        names = {n.lower() for n in self._auth_header_names}
        return {k: v for k, v in self.headers.items() if k.lower() not in names}

    def __repr__(self) -> str:
        proxy = "<set>" if self.proxy_url else "None"
        return (
            f"ResolvedScanConfig(target_value={self.target_value!r}, "
            f"target_type={self.target_type!r}, "
            f"headers=<{len(self.headers)} redacted>, "
            f"http_protocol={self.http_protocol!r}, intensity={self.intensity!r}, "
            f"proxy={proxy})"
        )

    __str__ = __repr__


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

    auth = _ctx_get(ctx, "auth") or {"auth_type": AuthType.NONE.value}
    extra_headers = _ctx_get(ctx, "extra_headers") or []
    ctx_headers = resolve_headers(auth, extra_headers)

    auth_header_names: list[str] = list(resolve_headers(auth))

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


def validate_overrides(overrides: dict | None) -> dict[str, dict]:
    """Keep only stage keys that exist and values their own config model accepts."""
    from stages.registry import stage_by_name  # noqa: PLC0415

    if not overrides:
        return {}
    specs = stage_by_name()
    clean: dict[str, dict] = {}
    for name, authored in overrides.items():
        spec = specs.get(name)
        values = authored
        if spec is not None and (spec.catalog_hidden or spec.always_on):
            values = (
                {k: v for k, v in values.items() if k != "enabled"}
                if isinstance(values, dict)
                else values
            )
            if spec.catalog_hidden or not values:
                continue
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
        except ValidationError as exc:
            first = exc.errors()[0]
            field = ".".join(str(part) for part in first.get("loc") or ())
            reason = str(first.get("msg", "")).removeprefix("Value error, ")
            where = f"{name}.{field}" if field else name
            raise _bad(f"{where}: {reason}"[:300]) from exc
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
    intensity: str | None = None,
) -> ResolvedScanConfig:
    from shared.enums.scan import INTENSITIES, Intensity  # noqa: PLC0415
    from stages.registry import rate_tools  # noqa: PLC0415
    from stages.registry import stages as stage_specs  # noqa: PLC0415

    run_intensity = intensity or engine.intensity
    if run_intensity not in INTENSITIES:
        msg = f"Intensity must be one of {', '.join(INTENSITIES)}."
        raise _bad(msg)
    passive = run_intensity == Intensity.PASSIVE.value

    ctx = context if context is not None else _NeutralContext()

    thread_mult = float(_ctx_get(ctx, "thread_multiplier", 1.0))
    timeout_mult = float(_ctx_get(ctx, "timeout_multiplier", 1.0))
    rate_overrides = _ctx_get(ctx, "per_tool_rate_overrides") or {}
    global_rate_limit_ceiling = _ctx_get(ctx, "global_rate_limit_override")

    headers, auth_header_names = _build_headers(engine, ctx)

    engine_transport = getattr(engine, "transport_overrides", None) or {}

    def _rate_override(tool: str) -> int | None:
        candidates = [
            int(v)
            for v in (
                rate_overrides.get(tool),
                (engine_transport.get(tool) or {}).get("rate"),
            )
            if v
        ]
        return _clamp(min(candidates), 1, MAX_RATE) if candidates else None

    def _thread_override(tool: str) -> int | None:
        value = (engine_transport.get(tool) or {}).get("threads")
        return int(value) if value else None

    stored = engine.stages or {}
    run_overrides = validate_overrides(overrides)
    stages: dict[str, dict] = {}
    transports: dict[str, dict] = {}
    per_tool_rate_limits: dict[str, int] = {}
    for tool in rate_tools():
        limit = tool_rate(
            tool,
            run_intensity,
            rate_override=_rate_override(tool),
            ceiling=global_rate_limit_ceiling,
        )
        if limit is not None:
            per_tool_rate_limits[tool] = limit

    for spec in stage_specs():
        authored = (
            {}
            if spec.catalog_hidden
            else {
                **(stored.get(spec.name) or {}),
                **(run_overrides.get(spec.name) or {}),
            }
        )
        if spec.always_on:
            authored["enabled"] = True
        config = spec.config_model(**authored)
        values = config.model_dump()
        if spec.transport_tool is not None:
            transports[spec.name] = spec.transport(
                run_intensity,
                thread_multiplier=thread_mult,
                timeout_multiplier=timeout_mult,
                rate_override=_rate_override(spec.transport_tool),
                thread_override=_thread_override(spec.transport_tool),
                ceiling=global_rate_limit_ceiling,
            ).as_dict()
        if passive and spec.touches_target and not spec.passive_capable:
            values["enabled"] = False
        stages[spec.name] = values

    excluded_subdomains = list(_ctx_get(ctx, "excluded_subdomains") or [])
    excluded_paths = list(_ctx_get(ctx, "excluded_paths") or [])
    excluded_ips = list(_ctx_get(ctx, "excluded_ips") or [])
    included_subdomains = list(_ctx_get(ctx, "included_subdomains") or [])

    follow_redirects = _ctx_get(ctx, "follow_redirects_override")
    http_protocol = (
        _ctx_get(ctx, "http_protocol", HttpProtocol.BOTH.value)
        or HttpProtocol.BOTH.value
    )

    config = ResolvedScanConfig(
        target_value=target_value,
        target_type=target_type,
        headers=headers,
        per_tool_rate_limits=per_tool_rate_limits,
        global_rate_limit_ceiling=global_rate_limit_ceiling,
        thread_multiplier=thread_mult,
        timeout_multiplier=timeout_mult,
        stages=stages,
        transports=transports,
        excluded_subdomains=excluded_subdomains,
        excluded_paths=excluded_paths,
        excluded_ips=excluded_ips,
        included_subdomains=included_subdomains,
        follow_redirects=follow_redirects,
        http_protocol=http_protocol,
        intensity=run_intensity,
        tool_options=dict(getattr(engine, "tool_options", None) or {}),
        overrides=run_overrides,
    )
    config._auth_header_names = auth_header_names
    config.proxy_url = proxy_url
    return config


_HEADER_LINE = r"^([ \t]*{name}[ \t]*:[ \t]*)([^\r\n]*(?:\r?\n[ \t]+[^\r\n]*)*)"
_MESSAGE_HEADER = re.compile(
    _HEADER_LINE.format(name=_CREDENTIAL_NAME), re.IGNORECASE | re.MULTILINE
)
_ERROR_HEADER = re.compile(
    rf"^([ \t]*{_CREDENTIAL_NAME}[ \t]*:[ \t]*)([^\r\n]*)", re.IGNORECASE | re.MULTILINE
)
_CREDENTIAL_HEADER_VALUE = re.compile(
    rf'({_HEADER_FLAG}["\']?{_CREDENTIAL_NAME}\s*:\s*)([^"\'\n]+?)'
    r'(?=["\']|\s+-{1,2}[A-Za-z]|\s*$)',
    re.IGNORECASE,
)
_QUERY_SECRET = re.compile(
    r"([?&;](?:[\w.\-]*(?:token|secret|password|passwd|api[_-]?key|apikey|signature)"
    r"|key|sig|auth|pass|pwd)=)([^&;#\s]*)",
    re.IGNORECASE,
)


def redact_credentials(command: str) -> str:
    """Mask proxy credentials, credential flags and credential header values in a command."""
    safe = _UNSAFE_CTRL.sub("", command or "")
    safe = PROXY_CREDS_RE.sub(rf"\1{MASK}@", safe)
    safe = _CREDENTIAL_HEADER_VALUE.sub(rf"\1{MASK}", safe)
    safe = _USER_FLAG.sub(rf"\1{MASK}", safe)
    return _CRED_FLAG.sub(rf"\1{MASK}", safe)


def _masked_header(found: re.Match) -> str:
    return found.group(1) + MASK if found.group(2).strip() else found.group(0)


def _split_message(text: str) -> tuple[str, str, str]:
    head, sep, body = text.partition("\r\n\r\n")
    if not sep:
        head, sep, body = text.partition("\n\n")
    return head, sep, body


def mask_header_values(text: str | None, names: Iterable[str]) -> str | None:
    """Mask the value of every named header in a raw HTTP message."""
    names = sorted({n.strip() for n in names if n and n.strip()}, key=len, reverse=True)
    if not text or not names:
        return text
    pattern = re.compile(
        _HEADER_LINE.format(name=f"(?:{'|'.join(re.escape(n) for n in names)})"),
        re.IGNORECASE | re.MULTILINE,
    )
    head, sep, body = _split_message(text)
    return pattern.sub(_masked_header, head) + sep + body


def redact_message(text: str | None) -> str | None:
    """Mask credential header values and query parameters in a raw HTTP request or response."""
    if not text:
        return text
    head, sep, body = _split_message(text)
    line, newline, rest = head.partition("\n")
    line = _QUERY_SECRET.sub(rf"\1{MASK}", line)
    return _MESSAGE_HEADER.sub(_masked_header, line + newline + rest) + sep + body
