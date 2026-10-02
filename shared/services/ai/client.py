"""One call surface over every provider."""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

from shared.definitions.ai import (
    BASE_URL_PROVIDERS,
    BILLED_REFUSALS,
    GATEWAY_TIMEOUTS,
    GOOGLE_GENERATE,
    MAX_MODEL_ID,
    MAX_OUTPUT_TOKENS,
    MODEL_LIST_PAGES,
    MODELS,
    REFUSAL,
    TASK_EFFORT,
    TASK_OUTPUT_TOKENS,
    UNREPORTED,
    US_INFERENCE,
    US_INFERENCE_PREMIUM,
    Charge,
    Effort,
    Rates,
    Usage,
    curated_rates,
    model_spec,
    openai_chat_model,
    same_model,
    us_premium,
)
from shared.enums.instance import AIProvider
from shared.http import egress_proxy
from shared.models.ai import AiModelList, AiModelOption
from shared.services.ai import ledger, prices
from shared.services.ai.config import AIConfig
from shared.services.ai.ledger import CallRecord
from shared.services.scan_resolve import MASK

_ANTHROPIC_API = "https://api.anthropic.com/v1"
_ANTHROPIC_VERSION = "2023-06-01"
_OPENAI_API = "https://api.openai.com/v1"
_OPENAI_URL = f"{_OPENAI_API}/chat/completions"
_GOOGLE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
_ANTHROPIC_THINKING: dict = {"type": "adaptive"}
_HTTP_ERROR = 400
_REDIRECT = 300
_PAGE_SIZE = 1000
_ERROR_CHARS = 300
_NESTED_ERRORS = 2
_NOT_JSON = "The provider answered with a body that is not JSON. Check the base URL."
_REDIRECTED = "The provider answered with a redirect. Check the base URL."
DECLINED = "The model declined the request."
_CAUSE_DEPTH = 4
# raised before the request reached the server
_UNSENT = frozenset(
    {
        "ConnectError",
        "ConnectTimeout",
        "PoolTimeout",
        "ProxyError",
        "UnsupportedProtocol",
        "InvalidURL",
        "LocalProtocolError",
        "WriteError",
        "WriteTimeout",
    }
)


class AIError(RuntimeError):
    """The provider could not answer."""

    def __init__(self, message: str, *, usage: Usage | None = None):
        super().__init__(message)
        self.usage = UNREPORTED if usage is None else usage


def chat_url(cfg: AIConfig) -> str:
    if cfg.provider == AIProvider.OPENAI.value:
        return _OPENAI_URL
    if cfg.provider == AIProvider.OPENAI_COMPATIBLE.value and cfg.base_url:
        return f"{cfg.base_url.rstrip('/')}/chat/completions"
    msg = f"Provider '{cfg.provider}' has no chat endpoint. Check the AI settings."
    raise AIError(msg, usage=Usage())


def models_url(cfg: AIConfig) -> str:
    if cfg.provider == AIProvider.ANTHROPIC.value:
        return f"{_ANTHROPIC_API}/models"
    if cfg.provider == AIProvider.OPENAI.value:
        return f"{_OPENAI_API}/models"
    if cfg.provider == AIProvider.GOOGLE.value:
        return _GOOGLE_URL
    if cfg.provider == AIProvider.OPENAI_COMPATIBLE.value and cfg.base_url:
        return f"{cfg.base_url.rstrip('/')}/models"
    msg = f"Provider '{cfg.provider}' has no model list. Check the AI settings."
    raise AIError(msg)


def provider_proxy(cfg: AIConfig) -> str | None:
    """The egress proxy, for a provider at a fixed public endpoint."""
    return None if cfg.provider in BASE_URL_PROVIDERS else egress_proxy()


def chat_headers(cfg: AIConfig) -> dict[str, str]:
    return {"Authorization": f"Bearer {cfg.api_key}"} if cfg.api_key else {}


def google_headers(cfg: AIConfig) -> dict[str, str]:
    return {"x-goog-api-key": cfg.api_key}


def models_headers(cfg: AIConfig) -> dict[str, str]:
    if cfg.provider == AIProvider.ANTHROPIC.value:
        return {
            "x-api-key": cfg.api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            **(anthropic_headers(cfg) or {}),
        }
    if cfg.provider == AIProvider.GOOGLE.value:
        return google_headers(cfg)
    return chat_headers(cfg)


def scrub_error(text: str, cfg: AIConfig) -> str:
    """Provider error text with no URL query, no URL credentials and no key."""
    clean = ledger.scrub(text)
    if cfg.api_key:
        clean = clean.replace(cfg.api_key, MASK)
    return " ".join(clean.split())[:_ERROR_CHARS]


def _text(value: object) -> str:
    return " ".join(value.split())[:_ERROR_CHARS] if isinstance(value, str) else ""


def provider_message(body: object, depth: int = 0) -> str:
    """The provider's own message from an error body, or an empty string."""
    if isinstance(body, bytes):
        body = body.decode(errors="replace")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except ValueError:
            return "" if "<" in body else _text(body)
    if isinstance(body, str):
        return _text(body)
    if isinstance(body, list) and body:
        body = body[0]
    if not isinstance(body, dict):
        return ""
    error = body.get("error")
    if isinstance(error, dict):
        return _upstream(error.get("metadata"), depth) or _text(error.get("message"))
    return _text(error) or _text(body.get("message")) or _text(body.get("detail"))


def _upstream(metadata: object, depth: int) -> str:
    """The message a routing provider nests from the model's own provider."""
    if depth >= _NESTED_ERRORS or not isinstance(metadata, dict):
        return ""
    inner = provider_message(metadata.get("raw"), depth + 1)
    name = _text(metadata.get("provider_name"))
    return f"{name}: {inner}" if inner and name else inner


def http_error(status: int, body: object, usage: Usage | None = None) -> AIError:
    message = provider_message(body)
    spent = (Usage() if usage is None else usage) + _answered(status, body)
    if not message:
        return AIError(f"Provider returned {status}.", usage=spent)
    return AIError(f"Provider returned {status}: {message}", usage=spent)


def _answered(status: int, body: object) -> Usage:
    """The usage an error answer carries, else nothing, else unknown for a gateway timeout."""
    found = _body_usage(body)
    if found is not None:
        return found
    return UNREPORTED if status in GATEWAY_TIMEOUTS else Usage()


def transport_usage(exc: BaseException) -> Usage:
    """Nothing when the request did not reach the server, else unknown."""
    seen: BaseException | None = exc
    for _ in range(_CAUSE_DEPTH):
        if seen is None:
            break
        if type(seen).__name__ in _UNSENT:
            return Usage()
        seen = seen.__cause__
    return UNREPORTED


def sdk_error(exc: Exception, usage: Usage | None = None) -> AIError:
    """An Anthropic SDK error as the provider's own message."""
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return http_error(status, getattr(exc, "body", None), usage)
    reason = str(exc) or type(exc).__name__
    spent = (Usage() if usage is None else usage) + transport_usage(exc)
    return AIError(f"The provider did not respond: {reason}", usage=spent)


# ---------- usage ----------


def _count(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(int(value), 0)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return 0


def _money(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        amount = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return amount if math.isfinite(amount) and amount >= 0 else None


def anthropic_usage(raw: object, model: str = "") -> Usage:
    """Anthropic counts cache reads and writes outside input_tokens."""
    if raw is None:
        return UNREPORTED
    reads = _count(getattr(raw, "cache_read_input_tokens", 0))
    writes = _count(getattr(raw, "cache_creation_input_tokens", 0))
    usage = Usage(
        _count(getattr(raw, "input_tokens", 0)) + reads + writes,
        _count(getattr(raw, "output_tokens", 0)),
        reads,
        writes,
    )
    if getattr(raw, "inference_geo", None) == US_INFERENCE and us_premium(model):
        return usage.at(US_INFERENCE_PREMIUM)
    return usage


def refused(message: object, usage: Usage) -> Usage:
    """A refusal's usage, billed at nothing when it came before any output in an unbilled category."""
    category = getattr(getattr(message, "stop_details", None), "category", None)
    if getattr(message, "content", None) or category in BILLED_REFUSALS:
        return usage
    return usage.at(0.0)


def openai_usage(raw: object) -> Usage:
    """OpenAI counts cached tokens inside prompt_tokens and reasoning inside completion_tokens."""
    if not isinstance(raw, dict):
        return UNREPORTED
    details = raw.get("prompt_tokens_details")
    details = details if isinstance(details, dict) else {}
    reads = _count(details.get("cached_tokens"))
    writes = _count(details.get("cache_write_tokens"))
    return Usage(
        max(_count(raw.get("prompt_tokens")), reads + writes),
        _count(raw.get("completion_tokens")),
        reads,
        writes,
        _reported_cost(raw),
    )


def _reported_cost(raw: dict) -> float | None:
    """A router's own charge in USD, plus what the upstream billed the account's own key."""
    cost = _money(raw.get("cost"))
    details = raw.get("cost_details")
    if cost is None or raw.get("is_byok") is not True or not isinstance(details, dict):
        return cost
    return cost + (_money(details.get("upstream_inference_cost")) or 0.0)


def google_usage(raw: object) -> Usage:
    """Google bills thoughts as output and counts cached content inside the prompt."""
    if not isinstance(raw, dict):
        return UNREPORTED
    reads = _count(raw.get("cachedContentTokenCount"))
    prompt = _count(raw.get("promptTokenCount")) + _count(
        raw.get("toolUsePromptTokenCount")
    )
    return Usage(
        max(prompt, reads),
        _count(raw.get("candidatesTokenCount")) + _count(raw.get("thoughtsTokenCount")),
        reads,
    )


def _body_usage(body: object) -> Usage | None:
    if isinstance(body, bytes | str):
        try:
            body = json.loads(body)
        except ValueError:
            return None
    found = body.get("usage") if isinstance(body, dict) else None
    return openai_usage(found) if isinstance(found, dict) else None


@dataclass
class AIResult:
    text: str
    model: str
    provider: str
    usage: Usage = field(default_factory=Usage)
    latency_ms: int = 0
    cached: bool = False
    charge: Charge = field(default_factory=Charge)

    @property
    def input_tokens(self) -> int:
        return self.usage.input_tokens

    @property
    def output_tokens(self) -> int:
        return self.usage.output_tokens


@dataclass
class AIUsage:
    calls: int = 0
    cached: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    failures: list[str] = field(default_factory=list)

    def record(self, result: AIResult) -> None:
        if result.cached:
            self.cached += 1
            return
        self.calls += 1
        self.input_tokens += result.input_tokens
        self.output_tokens += result.output_tokens

    def failed(self, task: str, exc: Exception) -> None:
        """A call that raised, with the tokens it spent."""
        spent = exc.usage if isinstance(exc, AIError) else UNREPORTED
        self.calls += 1
        self.input_tokens += spent.input_tokens
        self.output_tokens += spent.output_tokens
        self.failures.append(f"{task}: {exc}"[:300])


def complete(cfg: AIConfig, *, system: str, prompt: str, task: str) -> AIResult:
    model = cfg.model
    max_tokens = TASK_OUTPUT_TOKENS.get(task, MAX_OUTPUT_TOKENS)
    effort = TASK_EFFORT.get(task, Effort.LOW.value)
    started = time.monotonic()

    def write(usage: Usage, *, ok: bool, error: str | None = None) -> Charge:
        charge = cfg.charge(usage, model)
        ledger.record(
            CallRecord(
                task=task,
                provider=cfg.provider,
                model=model,
                ok=ok,
                usage=usage,
                charge=charge,
                latency_ms=int((time.monotonic() - started) * 1000),
                error=error,
            )
        )
        return charge

    try:
        if cfg.provider == AIProvider.ANTHROPIC.value:
            text, usage = _anthropic(cfg, model, system, prompt, max_tokens, effort)
        elif cfg.provider == AIProvider.GOOGLE.value:
            text, usage = _google(cfg, model, system, prompt, max_tokens)
        else:
            text, usage = _openai(cfg, model, system, prompt, max_tokens)
    except Exception as exc:
        spent = exc.usage if isinstance(exc, AIError) else UNREPORTED
        write(spent, ok=False, error=scrub_error(str(exc), cfg))
        raise

    latency = int((time.monotonic() - started) * 1000)
    charge = write(usage, ok=True)
    return AIResult(
        text=text.strip(),
        model=model,
        provider=cfg.provider,
        usage=usage,
        latency_ms=latency,
        charge=charge,
    )


def anthropic_headers(cfg: AIConfig) -> dict[str, str] | None:
    """The workspace header when one is configured."""
    return {"anthropic-workspace-id": cfg.workspace} if cfg.workspace else None


def anthropic_extras(model: str, effort: str) -> dict[str, Any]:
    """Thinking and effort parameters the model accepts."""
    spec = model_spec(model)
    extras: dict[str, Any] = {}
    if spec is None or spec.adaptive_thinking:
        extras["thinking"] = _ANTHROPIC_THINKING
    if spec is None or spec.supports_effort:
        extras["output_config"] = {"effort": effort}
    return extras


def _anthropic(
    cfg: AIConfig, model: str, system: str, prompt: str, max_tokens: int, effort: str
) -> tuple[str, Usage]:
    import anthropic  # noqa: PLC0415

    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
        **anthropic_extras(model, effort),
    }

    proxy = provider_proxy(cfg)
    client = anthropic.Anthropic(
        api_key=cfg.api_key,
        timeout=cfg.timeout,
        default_headers=anthropic_headers(cfg),
        http_client=anthropic.DefaultHttpxClient(proxy=proxy) if proxy else None,
    )
    try:
        response = client.messages.create(**kwargs)
    except anthropic.BadRequestError as exc:
        kwargs.pop("thinking", None)
        kwargs.pop("output_config", None)
        try:
            response = client.messages.create(**kwargs)
        except anthropic.APIError as retry_exc:
            raise sdk_error(retry_exc) from exc
    except anthropic.APIError as exc:
        raise sdk_error(exc) from exc

    usage = anthropic_usage(response.usage, model)
    if response.stop_reason == REFUSAL:
        raise AIError(DECLINED, usage=refused(response, usage))

    text = "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    )
    return text, usage


def _openai(
    cfg: AIConfig, model: str, system: str, prompt: str, max_tokens: int
) -> tuple[str, Usage]:
    payload = {
        "model": model,
        "max_completion_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }
    body = post_json(
        chat_url(cfg),
        payload,
        chat_headers(cfg),
        cfg.timeout,
        proxy=provider_proxy(cfg),
    )
    usage = openai_usage(body.get("usage"))
    choices = body.get("choices") or []
    if not choices:
        msg = "The provider returned no completion."
        raise AIError(msg, usage=usage)
    text = (choices[0].get("message") or {}).get("content") or ""
    return text, usage


def _google(
    cfg: AIConfig, model: str, system: str, prompt: str, max_tokens: int
) -> tuple[str, Usage]:
    url = f"{_GOOGLE_URL}/{model}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    body = post_json(
        url,
        payload,
        google_headers(cfg),
        cfg.timeout,
        proxy=provider_proxy(cfg),
    )
    usage = google_usage(body.get("usageMetadata"))
    candidates = body.get("candidates") or []
    if not candidates:
        msg = "The provider returned no completion."
        raise AIError(msg, usage=usage)
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(part.get("text", "") for part in parts)
    return text, usage


def post_json(
    url: str,
    payload: dict,
    headers: dict,
    timeout: float,
    *,
    proxy: str | None = None,
) -> dict:
    try:
        with httpx.Client(timeout=timeout, proxy=proxy) as client:
            response = client.post(url, json=payload, headers=headers)
            if response.status_code >= _HTTP_ERROR:
                raise http_error(response.status_code, response.text)
            body = response.json()
    except httpx.HTTPError as exc:
        msg = f"The provider did not respond: {exc}"
        raise AIError(msg, usage=transport_usage(exc)) from exc
    except ValueError as exc:
        raise AIError(_NOT_JSON) from exc
    if not isinstance(body, dict):
        raise AIError(_NOT_JSON)
    return body


# ---------- model listing ----------


@dataclass(frozen=True)
class _Listed:
    id: str
    label: str = ""
    rates: Rates | None = None


def list_models(
    cfg: AIConfig, *, transport: httpx.BaseTransport | None = None
) -> AiModelList:
    """The models the provider lists, merged with the curated and the live catalog."""
    try:
        listed = _listed(cfg, transport)
    except AIError as exc:
        return AiModelList(error=scrub_error(str(exc), cfg))
    except Exception as exc:
        return AiModelList(error=scrub_error(f"{type(exc).__name__}: {exc}", cfg))
    return AiModelList(
        models=_ranked(
            cfg.provider,
            listed,
            lambda m: prices.lookup(cfg.provider, m, base_url=cfg.base_url),
        )
    )


def listed_rates(cfg: AIConfig) -> Rates | None:
    """The price a server's own model list gives the connection's model. Raises when the list is not read."""
    listed = [item for item in _listed(cfg, None) if item.rates is not None]
    exact = next((item for item in listed if item.id == cfg.model), None)
    near = next((item for item in listed if same_model(item.id, cfg.model)), None)
    found = exact or near
    return found.rates if found else None


def current_rates(cfg: AIConfig) -> Rates | None:
    """The connection's model at today's price, or None when its server's list is not read."""
    if not cfg.model:
        return None
    if cfg.provider in BASE_URL_PROVIDERS:
        try:
            own = listed_rates(cfg)
        except Exception:
            return None
        if own is not None:
            return own
    return curated_rates(cfg.model) or prices.lookup(
        cfg.provider, cfg.model, base_url=cfg.base_url
    )


def _listed(cfg: AIConfig, transport: httpx.BaseTransport | None) -> list[_Listed]:
    url = models_url(cfg)
    headers = models_headers(cfg)
    with httpx.Client(
        timeout=cfg.timeout,
        proxy=None if transport else provider_proxy(cfg),
        transport=transport,
        follow_redirects=False,
    ) as client:
        if cfg.provider == AIProvider.ANTHROPIC.value:
            return _anthropic_models(client, url, headers)
        if cfg.provider == AIProvider.GOOGLE.value:
            return _google_models(client, url, headers)
        rows = _rows(_get_json(client, url, headers), "data")
        if cfg.provider == AIProvider.OPENAI.value:
            return [_Listed(r["id"]) for r in rows if openai_chat_model(r["id"])]
        return [_compatible(r) for r in rows]


def _anthropic_models(
    client: httpx.Client, url: str, headers: dict[str, str]
) -> list[_Listed]:
    out: list[_Listed] = []
    params: dict[str, Any] = {"limit": _PAGE_SIZE}
    for _ in range(MODEL_LIST_PAGES):
        body = _get_json(client, url, headers, params)
        out.extend(
            _Listed(r["id"], str(r.get("display_name") or ""))
            for r in _rows(body, "data")
        )
        last = body.get("last_id") if isinstance(body, dict) else None
        if not (isinstance(body, dict) and body.get("has_more") and last):
            break
        params = {"limit": _PAGE_SIZE, "after_id": last}
    return out


def _google_models(
    client: httpx.Client, url: str, headers: dict[str, str]
) -> list[_Listed]:
    out: list[_Listed] = []
    params: dict[str, Any] = {"pageSize": _PAGE_SIZE}
    for _ in range(MODEL_LIST_PAGES):
        body = _get_json(client, url, headers, params)
        for row in _rows(body, "models", key="name"):
            if GOOGLE_GENERATE not in (row.get("supportedGenerationMethods") or []):
                continue
            model_id = row["name"].removeprefix("models/")
            if model_id:
                out.append(_Listed(model_id, str(row.get("displayName") or "")))
        token = body.get("nextPageToken") if isinstance(body, dict) else None
        if not token:
            break
        params = {"pageSize": _PAGE_SIZE, "pageToken": token}
    return out


def _compatible(row: dict) -> _Listed:
    return _Listed(
        row["id"], str(row.get("name") or ""), prices.row_rates(row.get("pricing"))
    )


def _rows(body: object, field_name: str, *, key: str = "id") -> list[dict]:
    items = body.get(field_name) if isinstance(body, dict) else body
    if not isinstance(items, list):
        return []
    return [
        item
        for item in items
        if isinstance(item, dict) and isinstance(item.get(key), str) and item[key]
    ]


def _get_json(
    client: httpx.Client,
    url: str,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
) -> object:
    try:
        response = client.get(url, headers=headers, params=params)
    except httpx.HTTPError as exc:
        reason = str(exc) or type(exc).__name__
        msg = f"The provider did not respond: {reason}"
        raise AIError(msg) from exc
    if _REDIRECT <= response.status_code < _HTTP_ERROR:
        raise AIError(_REDIRECTED)
    if response.status_code >= _HTTP_ERROR:
        raise http_error(response.status_code, response.text)
    try:
        return response.json()
    except ValueError as exc:
        raise AIError(_NOT_JSON) from exc


_CATALOG_ORDER = {m.id: i for i, m in enumerate(MODELS)}


def _ranked(
    provider: str,
    listed: list[_Listed],
    live: Callable[[str], Rates | None] | None = None,
) -> list[AiModelOption]:
    ids = {item.id.strip() for item in listed}
    seen: dict[str, AiModelOption] = {}
    order: dict[str, int] = {}
    for item in listed:
        model_id = item.id.strip()
        if not model_id or model_id in seen or len(model_id) > MAX_MODEL_ID:
            continue
        spec = model_spec(model_id)
        curated = spec if spec is not None and spec.provider == provider else None
        recommended = bool(
            curated
            and curated.recommended
            and (curated.id == model_id or curated.id not in ids)
        )
        if curated is not None:
            order[model_id] = _CATALOG_ORDER[curated.id]
        rates = (
            item.rates
            or curated_rates(model_id)
            or (live(model_id) if live is not None else None)
        )
        seen[model_id] = AiModelOption(
            id=model_id,
            label=(curated.label if curated else item.label.strip()) or model_id,
            input_per_mtok=rates.input if rates else None,
            output_per_mtok=rates.output if rates else None,
            cache_read_per_mtok=rates.cache_read if rates else None,
            cache_write_per_mtok=rates.cache_write if rates else None,
            recommended=recommended,
        )
    return sorted(
        seen.values(),
        key=lambda m: (
            not m.recommended,
            order.get(m.id, 0) if m.recommended else 0,
            m.label.lower(),
            m.id,
        ),
    )
