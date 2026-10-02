"""A tool-using conversation over the configured provider."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from shared.definitions.ai import (
    MAX_OUTPUT_TOKENS,
    TASK_EFFORT,
    TASK_OUTPUT_TOKENS,
    Effort,
)
from shared.enums.instance import AIProvider
from shared.services.ai import ledger
from shared.services.ai.client import (
    AIError,
    anthropic_extras,
    anthropic_headers,
    chat_headers,
    chat_url,
    complete,
    post_json,
    provider_proxy,
)
from shared.services.ai.config import AIConfig
from shared.services.ai.ledger import CallRecord

TEXT = "text"
CALL = "call"
RESULT = "result"
DONE = "done"
ROUND_BREAK = "\n\n"
OUT_OF_BUDGET = "The answer ran past the output budget. Ask a narrower question."
NO_FINISH = "The model did not finish within the tool budget."
TOO_MANY_CALLS = "Skipped. At most {n} tool calls run in one turn."


@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    schema: dict


@dataclass
class AgentEvent:
    kind: str
    text: str = ""
    name: str = ""
    args: dict = field(default_factory=dict)
    ok: bool = True
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    rounds: int = 0


ToolCaller = Callable[[str, dict], Awaitable[tuple[str, bool]]]


@dataclass(frozen=True)
class _Budget:
    rounds: int
    calls: int

    def skipped(self) -> str:
        return TOO_MANY_CALLS.format(n=self.calls)


class _Voice:
    """Separates the text of one round from the next."""

    def __init__(self) -> None:
        self.spoke = False
        self.round_spoke = False

    def start_round(self) -> None:
        self.round_spoke = False

    def say(self, text: str) -> list[AgentEvent]:
        if not text:
            return []
        events = []
        if self.spoke and not self.round_spoke:
            events.append(AgentEvent(TEXT, text=ROUND_BREAK))
        self.spoke = self.round_spoke = True
        events.append(AgentEvent(TEXT, text=text))
        return events


async def converse(
    cfg: AIConfig,
    *,
    system: str,
    messages: list[dict[str, str]],
    tools: list[AgentTool],
    call_tool: ToolCaller,
    task: str,
    max_rounds: int,
    max_calls: int = 3,
) -> AsyncIterator[AgentEvent]:
    model = cfg.model_for_task(fast=False)
    max_tokens = TASK_OUTPUT_TOKENS.get(task, MAX_OUTPUT_TOKENS)
    effort = TASK_EFFORT.get(task, Effort.LOW.value)
    budget = _Budget(max_rounds, max_calls)
    if cfg.provider == AIProvider.ANTHROPIC.value:
        stream = _anthropic(
            cfg, model, system, messages, tools, call_tool, max_tokens, effort, budget
        )
    elif cfg.provider == AIProvider.GOOGLE.value:
        stream = _plain(cfg, system, messages, task)
    else:
        stream = _openai(
            cfg, model, system, messages, tools, call_tool, max_tokens, budget
        )
    if cfg.provider == AIProvider.GOOGLE.value:
        async for event in stream:
            yield event
        return

    started = time.monotonic()
    try:
        async for event in stream:
            if event.kind == DONE:
                ledger.record(
                    CallRecord(
                        task=task,
                        provider=cfg.provider,
                        model=event.model or model,
                        ok=True,
                        input_tokens=event.input_tokens,
                        output_tokens=event.output_tokens,
                        latency_ms=int((time.monotonic() - started) * 1000),
                        rounds=event.rounds or 1,
                    )
                )
            yield event
    except AIError as exc:
        ledger.record(
            CallRecord(
                task=task,
                provider=cfg.provider,
                model=model,
                ok=False,
                input_tokens=exc.input_tokens,
                output_tokens=exc.output_tokens,
                latency_ms=int((time.monotonic() - started) * 1000),
                error=str(exc),
            )
        )
        raise


def _request(
    model: str,
    max_tokens: int,
    system: str,
    history: list[dict[str, Any]],
    extras: dict[str, Any],
    specs: list[dict],
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": history,
        **extras,
    }
    if specs:
        kwargs["tools"] = specs
    return kwargs


async def _anthropic(
    cfg: AIConfig,
    model: str,
    system: str,
    messages: list[dict[str, str]],
    tools: list[AgentTool],
    call_tool: ToolCaller,
    max_tokens: int,
    effort: str,
    budget: _Budget,
) -> AsyncIterator[AgentEvent]:
    import anthropic  # noqa: PLC0415

    proxy = provider_proxy(cfg)
    client = anthropic.AsyncAnthropic(
        api_key=cfg.api_key,
        timeout=cfg.timeout,
        default_headers=anthropic_headers(cfg),
        http_client=anthropic.DefaultAsyncHttpxClient(proxy=proxy) if proxy else None,
    )
    history: list[dict[str, Any]] = [dict(m) for m in messages]
    specs = [
        {"name": t.name, "description": t.description, "input_schema": t.schema}
        for t in tools
    ]
    extras = anthropic_extras(model, effort)
    used_in = used_out = 0
    voice = _Voice()

    for round_no in range(1, budget.rounds + 1):
        kwargs = _request(model, max_tokens, system, history, extras, specs)
        voice.start_round()
        try:
            async with client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    for event in voice.say(text):
                        yield event
                final = await stream.get_final_message()
        except anthropic.BadRequestError as exc:
            if not extras:
                raise AIError(str(exc)) from exc
            extras = {}
            continue
        except anthropic.APIError as exc:
            raise AIError(str(exc)) from exc

        used_in += final.usage.input_tokens
        used_out += final.usage.output_tokens
        if final.stop_reason == "refusal":
            msg = "The model declined the request."
            raise AIError(msg, input_tokens=used_in, output_tokens=used_out)
        if final.stop_reason == "max_tokens" and not voice.round_spoke:
            raise AIError(OUT_OF_BUDGET, input_tokens=used_in, output_tokens=used_out)
        calls = [b for b in final.content if getattr(b, "type", "") == "tool_use"]
        if final.stop_reason != "tool_use" or not calls:
            yield AgentEvent(
                DONE,
                input_tokens=used_in,
                output_tokens=used_out,
                model=model,
                rounds=round_no,
            )
            return

        history.append({"role": "assistant", "content": final.content})
        results = []
        for index, call in enumerate(calls):
            args = call.input if isinstance(call.input, dict) else {}
            if index >= budget.calls:
                text, ok = budget.skipped(), False
            else:
                yield AgentEvent(CALL, name=call.name, args=args)
                text, ok = await call_tool(call.name, args)
                yield AgentEvent(RESULT, name=call.name, text=text, ok=ok)
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": call.id,
                    "content": text,
                    "is_error": not ok,
                }
            )
        history.append({"role": "user", "content": results})

    raise AIError(NO_FINISH, input_tokens=used_in, output_tokens=used_out)


async def _openai(
    cfg: AIConfig,
    model: str,
    system: str,
    messages: list[dict[str, str]],
    tools: list[AgentTool],
    call_tool: ToolCaller,
    max_tokens: int,
    budget: _Budget,
) -> AsyncIterator[AgentEvent]:
    history: list[dict[str, Any]] = [{"role": "system", "content": system}, *messages]
    specs = [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.schema,
            },
        }
        for t in tools
    ]
    headers = chat_headers(cfg)
    url = chat_url(cfg)
    proxy = provider_proxy(cfg)
    used_in = used_out = 0
    voice = _Voice()

    for round_no in range(1, budget.rounds + 1):
        payload: dict[str, Any] = {
            "model": model,
            "max_completion_tokens": max_tokens,
            "messages": history,
        }
        if specs:
            payload["tools"] = specs
        body = await asyncio.to_thread(
            post_json, url, payload, headers, cfg.timeout, proxy=proxy
        )
        choices = body.get("choices") or []
        if not choices:
            msg = "The provider returned no completion."
            raise AIError(msg)
        message = choices[0].get("message") or {}
        usage = body.get("usage") or {}
        used_in += int(usage.get("prompt_tokens", 0))
        used_out += int(usage.get("completion_tokens", 0))

        voice.start_round()
        for event in voice.say(message.get("content") or ""):
            yield event
        calls = message.get("tool_calls") or []
        if not calls:
            if choices[0].get("finish_reason") == "length" and not voice.round_spoke:
                raise AIError(
                    OUT_OF_BUDGET, input_tokens=used_in, output_tokens=used_out
                )
            yield AgentEvent(
                DONE,
                input_tokens=used_in,
                output_tokens=used_out,
                model=model,
                rounds=round_no,
            )
            return

        history.append(message)
        for index, call in enumerate(calls):
            fn = call.get("function") or {}
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except ValueError:
                args = {}
            if not isinstance(args, dict):
                args = {}
            name = str(fn.get("name") or "")
            if index >= budget.calls:
                text = budget.skipped()
            else:
                yield AgentEvent(CALL, name=name, args=args)
                text, ok = await call_tool(name, args)
                yield AgentEvent(RESULT, name=name, text=text, ok=ok)
            history.append(
                {"role": "tool", "tool_call_id": call.get("id"), "content": text}
            )

    raise AIError(NO_FINISH, input_tokens=used_in, output_tokens=used_out)


async def _plain(
    cfg: AIConfig, system: str, messages: list[dict[str, str]], task: str
) -> AsyncIterator[AgentEvent]:
    """One answer with no tools."""
    lines = [f"{m['role'].capitalize()}: {m['content']}" for m in messages]
    prompt = "\n\n".join(lines)
    result = await asyncio.to_thread(
        complete, cfg, system=system, prompt=prompt, task=task
    )
    yield AgentEvent(TEXT, text=result.text)
    yield AgentEvent(
        DONE,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        model=result.model,
    )
