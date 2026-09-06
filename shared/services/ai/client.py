"""One call surface over every provider. A failure here never fails a report."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx

from shared.definitions.ai import (
    MAX_OUTPUT_TOKENS,
    MODEL_BY_ID,
    TASK_EFFORT,
    TASK_OUTPUT_TOKENS,
    Effort,
)
from shared.enums.instance import AIProvider
from shared.logging import get_logger
from shared.services.ai.config import AIConfig

logger = get_logger(__name__)

_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_GOOGLE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
_ANTHROPIC_THINKING: dict = {"type": "adaptive"}
_HTTP_ERROR = 400


class AIError(RuntimeError):
    """The provider could not answer."""


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

    if cfg.provider == AIProvider.ANTHROPIC.value:
        text, tokens = _anthropic(cfg, model, system, prompt, max_tokens, effort)
    elif cfg.provider == AIProvider.GOOGLE.value:
        text, tokens = _google(cfg, model, system, prompt, max_tokens)
    else:
        text, tokens = _openai(cfg, model, system, prompt, max_tokens)

    return AIResult(
        text=text.strip(),
        model=model,
        provider=cfg.provider,
        input_tokens=tokens[0],
        output_tokens=tokens[1],
        latency_ms=int((time.monotonic() - started) * 1000),
    )


def count_tokens(cfg: AIConfig, *, system: str, prompt: str, fast: bool = False) -> int:
    model = cfg.model_for_task(fast=fast)
    if cfg.provider == AIProvider.ANTHROPIC.value:
        try:
            import anthropic  # noqa: PLC0415

            client = _anthropic_client(anthropic, cfg)
            counted = client.messages.count_tokens(
                model=model,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return int(counted.input_tokens)
        except Exception:
            logger.debug("token count unavailable, estimating")
    return _estimate_tokens(system) + _estimate_tokens(prompt)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _anthropic_client(anthropic, cfg: AIConfig):
    """A key that is not workspace scoped needs the workspace named on every request."""
    headers = {"anthropic-workspace-id": cfg.workspace} if cfg.workspace else None
    return anthropic.Anthropic(
        api_key=cfg.api_key, timeout=cfg.timeout, default_headers=headers
    )


def _anthropic(
    cfg: AIConfig, model: str, system: str, prompt: str, max_tokens: int, effort: str
) -> tuple[str, tuple[int, int]]:
    import anthropic  # noqa: PLC0415

    spec = MODEL_BY_ID.get(model)
    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }
    if spec is None or spec.adaptive_thinking:
        kwargs["thinking"] = _ANTHROPIC_THINKING
    if spec is None or spec.supports_effort:
        kwargs["output_config"] = {"effort": effort}

    client = _anthropic_client(anthropic, cfg)
    try:
        response = client.messages.create(**kwargs)
    except anthropic.BadRequestError as exc:
        # a model that rejects thinking or effort still answers without them
        kwargs.pop("thinking", None)
        kwargs.pop("output_config", None)
        try:
            response = client.messages.create(**kwargs)
        except anthropic.APIError as retry_exc:
            raise AIError(str(retry_exc)) from exc
    except anthropic.APIError as exc:
        raise AIError(str(exc)) from exc

    if response.stop_reason == "refusal":
        msg = "The model declined to answer this request."
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
    headers = {"Authorization": f"Bearer {cfg.api_key}"}
    body = _post(_OPENAI_URL, payload, headers, cfg.timeout)
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
    body = _post(url, payload, {"x-goog-api-key": cfg.api_key}, cfg.timeout)
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


def _post(url: str, payload: dict, headers: dict, timeout: float) -> dict:
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload, headers=headers)
            if response.status_code >= _HTTP_ERROR:
                detail = response.text[:300]
                msg = f"Provider returned {response.status_code}: {detail}"
                raise AIError(msg)
            return response.json()
    except httpx.HTTPError as exc:
        msg = f"Could not reach the provider: {exc}"
        raise AIError(msg) from exc
