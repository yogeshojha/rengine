"""A tool-using conversation over the configured provider."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field, replace
from typing import Any

from shared.definitions.ai import (
    MAX_OUTPUT_TOKENS,
    REFUSAL,
    TASK_EFFORT,
    TASK_OUTPUT_TOKENS,
    UNREPORTED,
    Charge,
    Effort,
    Usage,
    price,
)
from shared.enums.instance import AIProvider
from shared.services.ai import ledger
from shared.services.ai.client import (
    DECLINED,
    AIError,
    anthropic_extras,
    anthropic_headers,
    anthropic_usage,
    chat_headers,
    chat_url,
    complete,
    google_headers,
    google_url,
    google_usage,
    openai_usage,
    post_json,
    provider_proxy,
    refused,
    scrub_error,
    sdk_error,
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
STOPPED = "Stopped before the answer finished."
NO_COMPLETION = "The provider returned no completion."
# the shortest system prompt sent with a cache breakpoint
CACHE_SYSTEM_CHARS = 6_000
_GOOGLE_DROP = frozenset(
    {"title", "default", "additionalProperties", "examples", "$schema"}
)
_GOOGLE_DECLINED = frozenset(
    {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION"}
)
_GOOGLE_DONE = "STOP"
_GOOGLE_LENGTH = "MAX_TOKENS"
# thinking allowance added to Gemini's maxOutputTokens
GOOGLE_THINKING_TOKENS = 8_192
STOPPED_WITHOUT_ANSWER = "The model stopped without an answer. Reason: {reason}."


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
    usage: Usage = field(default_factory=Usage)
    model: str = ""
    rounds: int = 0
    charge: Charge | None = None

    @property
    def input_tokens(self) -> int:
        return self.usage.input_tokens

    @property
    def output_tokens(self) -> int:
        return self.usage.output_tokens


ToolCaller = Callable[[str, dict], Awaitable[tuple[str, bool]]]
Write = Callable[[Usage], object]


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


def _read(live: Callable[[], Usage] | None) -> Usage:
    if live is None:
        return Usage()
    try:
        return live()
    except Exception:
        return UNREPORTED


class Tally:
    """What one conversation has spent, the round in flight included."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._done = Usage()
        self._live: Callable[[], Usage] | None = None
        self._flights = 0
        self._write: Write | None = None
        self._waiting = False
        self.rounds = 0
        self.settled = False

    def start(self, live: Callable[[], Usage] | None = None) -> None:
        """A round opened, with what its provider has reported so far."""
        with self._lock:
            self.rounds += 1
            self._live = live

    def close(self, usage: Usage | None = None) -> None:
        """A round ended, with its final usage or what it last reported."""
        with self._lock:
            ended = usage if usage is not None else _read(self._live)
            self._done = self._done + ended
            self._live = None

    def total(self) -> Usage:
        with self._lock:
            return self._done + _read(self._live)

    def lift(self) -> None:
        """A blocking request left on another thread."""
        with self._lock:
            self.rounds += 1
            self._flights += 1

    def land(self, usage: Usage) -> None:
        """That request returned, after the conversation ended or not."""
        with self._lock:
            self._flights -= 1
            if not self.settled or self._write is None:
                self._done = self._done + usage
                return
            if self._waiting:
                self._done = self._done + usage
                if self._flights:
                    return
                self._waiting = False
                usage = self._done
            write = self._write
        write(usage)

    def settle(self, write: Write) -> None:
        """Write the spend now, or once the requests in flight return."""
        with self._lock:
            if self.settled:
                return
            self.settled = True
            self._write = write
            if self._flights:
                self._waiting = True
                return
            spent = self._done + _read(self._live)
        write(spent)

    def mark(self) -> None:
        with self._lock:
            self.settled = True


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
    stable_system: bool = False,
) -> AsyncIterator[AgentEvent]:
    model = cfg.model
    if cfg.provider == AIProvider.GOOGLE.value and not tools:
        async for event in _plain(cfg, system, messages, task):
            yield event
        return

    max_tokens = TASK_OUTPUT_TOKENS.get(task, MAX_OUTPUT_TOKENS)
    effort = TASK_EFFORT.get(task, Effort.LOW.value)
    budget = _Budget(max_rounds, max_calls)
    rates = cfg.known_rates(model) or await asyncio.to_thread(cfg.rates, model)
    tally = Tally()
    source = ledger.current()
    started = time.monotonic()

    def write(
        usage: Usage, *, ok: bool, error: str | None = None, rounds: int = 0
    ) -> Charge:
        charge = price(usage, rates, cfg.provider)
        ledger.record(
            CallRecord(
                task=task,
                provider=cfg.provider,
                model=model,
                ok=ok,
                usage=usage,
                charge=charge,
                latency_ms=int((time.monotonic() - started) * 1000),
                rounds=rounds or max(tally.rounds, 1),
                error=error,
                source=source,
            )
        )
        return charge

    def failed(error: str) -> Write:
        return lambda usage: write(usage, ok=False, error=error)

    if cfg.provider == AIProvider.ANTHROPIC.value:
        stream = _anthropic(
            cfg,
            model,
            system,
            messages,
            tools,
            call_tool,
            max_tokens,
            effort,
            budget,
            tally,
            stable_system=stable_system,
        )
    elif cfg.provider == AIProvider.GOOGLE.value:
        stream = _google(
            cfg, model, system, messages, tools, call_tool, max_tokens, budget, tally
        )
    else:
        stream = _openai(
            cfg, model, system, messages, tools, call_tool, max_tokens, budget, tally
        )

    try:
        async for event in stream:
            if event.kind == DONE and not tally.settled:
                tally.mark()
                event.charge = write(event.usage, ok=True, rounds=event.rounds)
            yield event
    except AIError as exc:
        if not tally.settled:
            tally.mark()
            write(exc.usage, ok=False, error=scrub_error(str(exc), cfg))
        raise
    except Exception as exc:
        tally.settle(failed(scrub_error(f"{type(exc).__name__}: {exc}", cfg)))
        raise
    except BaseException:
        tally.settle(failed(STOPPED))
        raise


def _request(
    model: str,
    max_tokens: int,
    system: str,
    history: list[dict[str, Any]],
    extras: dict[str, Any],
    specs: list[dict],
    stable_system: bool = False,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": _system(system, stable=stable_system),
        "messages": history,
        **extras,
    }
    if specs:
        kwargs["tools"] = specs
    return kwargs


def _system(system: str, *, stable: bool) -> str | list[dict[str, Any]]:
    if not stable or len(system) < CACHE_SYSTEM_CHARS:
        return system
    return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]


def _snapshot(stream: Any, model: str) -> Callable[[], Usage]:
    """What a round in flight has reported, short of its final usage."""
    return lambda: replace(
        anthropic_usage(stream.current_message_snapshot.usage, model), reported=False
    )


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
    tally: Tally,
    stable_system: bool = False,
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
    voice = _Voice()

    for round_no in range(1, budget.rounds + 1):
        kwargs = _request(
            model, max_tokens, system, history, extras, specs, stable_system
        )
        voice.start_round()
        try:
            async with client.messages.stream(**kwargs) as stream:
                tally.start(_snapshot(stream, model))
                async for text in stream.text_stream:
                    for event in voice.say(text):
                        yield event
                final = await stream.get_final_message()
        except anthropic.BadRequestError as exc:
            tally.close()
            if not extras:
                raise sdk_error(exc, tally.total()) from exc
            extras = {}
            continue
        except anthropic.APIError as exc:
            raise sdk_error(exc, tally.total()) from exc

        spent = anthropic_usage(final.usage, model)
        if final.stop_reason == REFUSAL:
            tally.close(refused(final, spent))
            raise AIError(DECLINED, usage=tally.total())
        tally.close(spent)
        if final.stop_reason == "max_tokens" and not voice.round_spoke:
            raise AIError(OUT_OF_BUDGET, usage=tally.total())
        calls = [b for b in final.content if getattr(b, "type", "") == "tool_use"]
        if final.stop_reason != "tool_use" or not calls:
            yield AgentEvent(DONE, usage=tally.total(), model=model, rounds=round_no)
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

    raise AIError(NO_FINISH, usage=tally.total())


def _openai_spent(body: dict) -> Usage:
    return openai_usage(body.get("usage"))


def _google_spent(body: dict) -> Usage:
    return google_usage(body.get("usageMetadata"))


def _post_round(
    tally: Tally,
    url: str,
    payload: dict,
    headers: dict,
    timeout: float,
    proxy: str | None,
    spent_in: Callable[[dict], Usage] = _openai_spent,
) -> dict:
    tally.lift()
    spent = UNREPORTED
    try:
        body = post_json(url, payload, headers, timeout, proxy=proxy)
        spent = spent_in(body)
        return body
    except AIError as exc:
        spent = exc.usage
        raise
    finally:
        tally.land(spent)


async def _openai(
    cfg: AIConfig,
    model: str,
    system: str,
    messages: list[dict[str, str]],
    tools: list[AgentTool],
    call_tool: ToolCaller,
    max_tokens: int,
    budget: _Budget,
    tally: Tally,
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
    voice = _Voice()

    for round_no in range(1, budget.rounds + 1):
        payload: dict[str, Any] = {
            "model": model,
            "max_completion_tokens": max_tokens,
            "messages": history,
        }
        if specs:
            payload["tools"] = specs
        try:
            body = await asyncio.to_thread(
                _post_round, tally, url, payload, headers, cfg.timeout, proxy
            )
        except AIError as exc:
            exc.usage = tally.total()
            raise
        choices = body.get("choices") or []
        if not choices:
            raise AIError(NO_COMPLETION, usage=tally.total())
        message = choices[0].get("message") or {}

        voice.start_round()
        for event in voice.say(message.get("content") or ""):
            yield event
        calls = message.get("tool_calls") or []
        if not calls:
            if choices[0].get("finish_reason") == "length" and not voice.round_spoke:
                raise AIError(OUT_OF_BUDGET, usage=tally.total())
            yield AgentEvent(DONE, usage=tally.total(), model=model, rounds=round_no)
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

    raise AIError(NO_FINISH, usage=tally.total())


def google_schema(schema: Any) -> Any:
    """A tool's JSON schema in the subset Gemini function declarations accept."""
    if not isinstance(schema, dict):
        return schema
    options = schema.get("anyOf")
    if isinstance(options, list):
        kept = [
            o for o in options if not (isinstance(o, dict) and o.get("type") == "null")
        ]
        if len(kept) == 1 and isinstance(kept[0], dict):
            merged = {k: v for k, v in schema.items() if k != "anyOf"} | kept[0]
            return google_schema(merged) | {"nullable": True}
    out: dict[str, Any] = {}
    for key, value in schema.items():
        if key in _GOOGLE_DROP:
            continue
        if key == "properties" and isinstance(value, dict):
            out[key] = {name: google_schema(sub) for name, sub in value.items()}
        elif key in ("items", "anyOf"):
            out[key] = (
                [google_schema(v) for v in value]
                if isinstance(value, list)
                else google_schema(value)
            )
        else:
            out[key] = value
    return out


def _declaration(tool: AgentTool) -> dict[str, Any]:
    out: dict[str, Any] = {"name": tool.name, "description": tool.description}
    params = google_schema(tool.schema)
    if isinstance(params, dict) and params.get("properties"):
        out["parameters"] = params
    return out


async def _google(
    cfg: AIConfig,
    model: str,
    system: str,
    messages: list[dict[str, str]],
    tools: list[AgentTool],
    call_tool: ToolCaller,
    max_tokens: int,
    budget: _Budget,
    tally: Tally,
) -> AsyncIterator[AgentEvent]:
    contents: list[dict[str, Any]] = [
        {
            "role": "model" if m["role"] == "assistant" else "user",
            "parts": [{"text": m["content"]}],
        }
        for m in messages
    ]
    declarations = [_declaration(t) for t in tools]
    url = google_url(model)
    headers = google_headers(cfg)
    proxy = provider_proxy(cfg)
    voice = _Voice()

    for round_no in range(1, budget.rounds + 1):
        payload: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens + GOOGLE_THINKING_TOKENS
            },
        }
        if declarations:
            payload["tools"] = [{"functionDeclarations": declarations}]
        try:
            body = await asyncio.to_thread(
                _post_round,
                tally,
                url,
                payload,
                headers,
                cfg.timeout,
                proxy,
                _google_spent,
            )
        except AIError as exc:
            exc.usage = tally.total()
            raise
        candidates = body.get("candidates") or []
        if not candidates:
            blocked = (body.get("promptFeedback") or {}).get("blockReason")
            raise AIError(DECLINED if blocked else NO_COMPLETION, usage=tally.total())
        candidate = candidates[0]
        parts = (candidate.get("content") or {}).get("parts") or []
        finish = candidate.get("finishReason")

        voice.start_round()
        said = "".join(
            str(p.get("text") or "")
            for p in parts
            if isinstance(p, dict) and not p.get("thought")
        )
        for event in voice.say(said):
            yield event
        calls = [
            p["functionCall"]
            for p in parts
            if isinstance(p, dict) and isinstance(p.get("functionCall"), dict)
        ]
        if not calls:
            if finish in _GOOGLE_DECLINED:
                raise AIError(DECLINED, usage=tally.total())
            if not voice.round_spoke and finish == _GOOGLE_LENGTH:
                raise AIError(OUT_OF_BUDGET, usage=tally.total())
            if not voice.round_spoke and finish not in (None, _GOOGLE_DONE):
                reason = STOPPED_WITHOUT_ANSWER.format(reason=finish)
                raise AIError(reason, usage=tally.total())
            yield AgentEvent(DONE, usage=tally.total(), model=model, rounds=round_no)
            return

        contents.append({"role": "model", "parts": parts})
        replies: list[dict[str, Any]] = []
        for index, call in enumerate(calls):
            name = str(call.get("name") or "")
            args = call.get("args") if isinstance(call.get("args"), dict) else {}
            if index >= budget.calls:
                text, ok = budget.skipped(), False
            else:
                yield AgentEvent(CALL, name=name, args=args)
                text, ok = await call_tool(name, args)
                yield AgentEvent(RESULT, name=name, text=text, ok=ok)
            answer: dict[str, Any] = {
                "name": name,
                "response": {"content": text, "ok": ok},
            }
            if call.get("id"):
                answer["id"] = call["id"]
            replies.append({"functionResponse": answer})
        contents.append({"role": "user", "parts": replies})

    raise AIError(NO_FINISH, usage=tally.total())


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
        usage=result.usage,
        model=result.model,
        rounds=1,
        charge=result.charge,
    )
