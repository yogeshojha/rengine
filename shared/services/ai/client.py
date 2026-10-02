"""One call surface over every provider."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from shared.definitions.ai import (
    BASE_URL_PROVIDERS,
    MAX_OUTPUT_TOKENS,
    MODEL_BY_ID,
    TASK_EFFORT,
    TASK_OUTPUT_TOKENS,
    Effort,
)
from shared.enums.instance import AIProvider
from shared.http import egress_proxy
from shared.services.ai import ledger
from shared.services.ai.config import AIConfig
from shared.services.ai.ledger import CallRecord

_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_GOOGLE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
_ANTHROPIC_THINKING: dict = {"type": "adaptive"}
_HTTP_ERROR = 400
_NOT_JSON = "The provider answered with a body that is not JSON. Check the base URL."


class AIError(RuntimeError):
    """The provider could not answer."""

    def __init__(self, message: str, *, input_tokens: int = 0, output_tokens: int = 0):
        super().__init__(message)
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


def chat_url(cfg: AIConfig) -> str:
    if cfg.provider == AIProvider.OPENAI.value:
        return _OPENAI_URL
    if cfg.provider == AIProvider.OPENAI_COMPATIBLE.value and cfg.base_url:
        return f"{cfg.base_url.rstrip('/')}/chat/completions"
    msg = f"Provider '{cfg.provider}' has no chat endpoint. Check the AI settings."
    raise AIError(msg)


def provider_proxy(cfg: AIConfig) -> str | None:
    """The egress proxy, for a provider at a fixed public endpoint."""
    return None if cfg.provider in BASE_URL_PROVIDERS else egress_proxy()


def chat_headers(cfg: AIConfig) -> dict[str, str]:
    return {"Authorization": f"Bearer {cfg.api_key}"} if cfg.api_key else {}


@dataclass
class AIResult:
    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    cached: bool = False


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


def complete(
    cfg: AIConfig,
    *,
    system: str,
    prompt: str,
    task: str,
    fast: bool = False,
) -> AIResult:
    model = cfg.model_for_task(fast=fast)
    max_tokens = TASK_OUTPUT_TOKENS.get(task, MAX_OUTPUT_TOKENS)
    effort = TASK_EFFORT.get(task, Effort.LOW.value)
    started = time.monotonic()

    try:
        if cfg.provider == AIProvider.ANTHROPIC.value:
            text, tokens = _anthropic(cfg, model, system, prompt, max_tokens, effort)
        elif cfg.provider == AIProvider.GOOGLE.value:
            text, tokens = _google(cfg, model, system, prompt, max_tokens)
        else:
            text, tokens = _openai(cfg, model, system, prompt, max_tokens)
    except Exception as exc:
        ledger.record(
            CallRecord(
                task=task,
                provider=cfg.provider,
                model=model,
                ok=False,
                latency_ms=int((time.monotonic() - started) * 1000),
                error=str(exc),
            )
        )
        raise

    result = AIResult(
        text=text.strip(),
        model=model,
        provider=cfg.provider,
        input_tokens=tokens[0],
        output_tokens=tokens[1],
        latency_ms=int((time.monotonic() - started) * 1000),
    )
    ledger.record(
        CallRecord(
            task=task,
            provider=cfg.provider,
            model=model,
            ok=True,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            latency_ms=result.latency_ms,
        )
    )
    return result


def anthropic_headers(cfg: AIConfig) -> dict[str, str] | None:
    """The workspace header when one is configured."""
    return {"anthropic-workspace-id": cfg.workspace} if cfg.workspace else None


def anthropic_extras(model: str, effort: str) -> dict[str, Any]:
    """Thinking and effort parameters the model accepts."""
    spec = MODEL_BY_ID.get(model)
    extras: dict[str, Any] = {}
    if spec is None or spec.adaptive_thinking:
        extras["thinking"] = _ANTHROPIC_THINKING
    if spec is None or spec.supports_effort:
        extras["output_config"] = {"effort": effort}
    return extras


def _anthropic(
    cfg: AIConfig, model: str, system: str, prompt: str, max_tokens: int, effort: str
) -> tuple[str, tuple[int, int]]:
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
            raise AIError(str(retry_exc)) from exc
    except anthropic.APIError as exc:
        raise AIError(str(exc)) from exc

    if response.stop_reason == "refusal":
        msg = "The model declined the request."
        raise AIError(msg)

    text = "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    )
    return text, (response.usage.input_tokens, response.usage.output_tokens)


def _openai(
    cfg: AIConfig, model: str, system: str, prompt: str, max_tokens: int
) -> tuple[str, tuple[int, int]]:
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
    choices = body.get("choices") or []
    if not choices:
        msg = "The provider returned no completion."
        raise AIError(msg)
    text = (choices[0].get("message") or {}).get("content") or ""
    usage = body.get("usage") or {}
    return text, (
        int(usage.get("prompt_tokens", 0)),
        int(usage.get("completion_tokens", 0)),
    )


def _google(
    cfg: AIConfig, model: str, system: str, prompt: str, max_tokens: int
) -> tuple[str, tuple[int, int]]:
    url = f"{_GOOGLE_URL}/{model}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    body = post_json(
        url,
        payload,
        {"x-goog-api-key": cfg.api_key},
        cfg.timeout,
        proxy=provider_proxy(cfg),
    )
    candidates = body.get("candidates") or []
    if not candidates:
        msg = "The provider returned no completion."
        raise AIError(msg)
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(part.get("text", "") for part in parts)
    usage = body.get("usageMetadata") or {}
    return text, (
        int(usage.get("promptTokenCount", 0)),
        int(usage.get("candidatesTokenCount", 0)),
    )


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
                detail = response.text[:300]
                msg = f"Provider returned {response.status_code}: {detail}"
                raise AIError(msg)
            body = response.json()
    except httpx.HTTPError as exc:
        msg = f"The provider did not respond: {exc}"
        raise AIError(msg) from exc
    except ValueError as exc:
        raise AIError(_NOT_JSON) from exc
    if not isinstance(body, dict):
        raise AIError(_NOT_JSON)
    return body
