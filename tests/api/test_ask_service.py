"""Ask end to end: threads, ownership, the streamed reply and what it stores."""

from __future__ import annotations

import json
import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.services.ask import service as ask_service
from app.services.ask.service import AskService, reply
from shared.definitions.ask import (
    MAX_THREADS_PER_FINDING,
    CitationKind,
    MessageRole,
    StreamEvent,
    TraceStatus,
    Verdict,
)
from shared.definitions.evidence import Evidence
from shared.definitions.surface import SurfaceDimension
from shared.models.ask import AskQuestion, AskThreadCreate, TraceStep
from shared.models.user import User
from shared.models.vulnerability import Vulnerability
from shared.services.ai.agent import CALL, DONE, RESULT, TEXT, AgentEvent
from shared.services.ai.client import AIError
from shared.services.ai.config import AIConfig

pytestmark = pytest.mark.api

HOST = "git.example.com"
RESPONSE = (
    "HTTP/1.1 200 OK\ncontent-type: application/json\n\n"
    '{\n  "email": "owner@example.com",\n  "status": "ok"\n}'
)


@pytest.fixture
def flush_only(estate, monkeypatch):
    monkeypatch.setattr(estate.session, "commit", estate.session.flush)
    monkeypatch.setattr(
        estate.session.sync_session, "commit", estate.session.sync_session.flush
    )


def _fp() -> str:
    return uuid.uuid4().hex * 2


async def _finding(
    estate, *, at, fp: str, response: str | None = RESPONSE, scan: str = "run"
) -> uuid.UUID:
    sid = estate.scans[scan]
    row = Vulnerability(
        project_id=estate.project_id,
        scan_id=sid,
        target_id=estate.targets["example.com"],
        fingerprint=fp,
        template_id="gitlab-reset",
        template_name="GitLab reset",
        severity="critical",
        matched_at=f"https://{HOST}/users/password",
        host=HOST,
        matcher_name="word-1",
        extracted_results=["owner@example.com"],
        request="POST /users/password HTTP/1.1",
        response=response,
        evidence=Evidence.OBSERVED.value,
        discovered_at=at,
    )
    estate.session.add(row)
    await estate.session.flush()
    return row.id


async def _user(estate) -> User:
    tag = uuid.uuid4().hex[:8]
    row = User(username=f"u{tag}", email=f"{tag}@test.local", hashed_password="x")
    estate.session.add(row)
    await estate.session.flush()
    return row


def _cfg() -> AIConfig:
    return AIConfig(
        provider="anthropic",
        api_key="k",
        model="claude-opus-5",
        fast_model="claude-haiku-4-5",
        features={"ask": True},
    )


def _fake_converse(events, seen: dict):
    async def converse(
        cfg, *, system, messages, tools, call_tool, task, max_rounds, max_calls=3
    ):
        seen["system"] = system
        seen["messages"] = messages
        seen["tools"] = [t.name for t in tools]
        for event in events:
            if isinstance(event, Exception):
                raise event
            if event.kind == CALL:
                text, ok = await call_tool(event.name, event.args)
                seen.setdefault("tool_text", []).append(text)
                yield event
                yield AgentEvent(RESULT, name=event.name, text=text, ok=ok)
            else:
                yield event

    return converse


async def _fake_call(ctx, name, args):
    step = TraceStep(
        tool=name,
        label="Query assets",
        status=TraceStatus.DONE.value,
        rows=3,
        pivot="https://ui/surface/web_assets?q=tech:gitlab",
        ms=4,
    )
    return '{"summary": "3 rows"}', step


async def _collect(stream) -> list[tuple[str, dict]]:
    out = []
    async for chunk in stream:
        event, data = chunk.split("\n", 1)
        out.append((event.removeprefix("event: "), json.loads(data[6:].strip())))
    return out


@pytest.fixture
async def ready(estate, now, monkeypatch, flush_only):
    await estate.scan("example.com", "run", at=now)
    fp = _fp()
    vuln_id = await _finding(estate, at=now, fp=fp)
    monkeypatch.setattr(ask_service, "load_config_async", _cfg_loader(_cfg()))
    monkeypatch.setattr(ask_service.limits, "exceeded", _never)
    monkeypatch.setattr(ask_service.budget, "over_daily", _not_over)
    monkeypatch.setattr(ask_service.tools, "call", _fake_call)
    thread = await AskService(estate.session).create(
        estate.user_id,
        estate.project_id,
        AskThreadCreate(target_id=estate.targets["example.com"], asset_key=fp),
    )
    user = await estate.session.get(User, estate.user_id)
    return {"fp": fp, "vuln_id": vuln_id, "thread": thread, "user": user}


def _cfg_loader(cfg):
    async def load(session):
        return cfg

    return load


async def _never(token_id, limit):
    return False


async def _not_over(user_id):
    return False


async def test_create_requires_the_finding_on_the_target(estate, now, flush_only):
    await estate.scan("example.com", "run", at=now)
    fp = _fp()
    service = AskService(estate.session)
    body = AskThreadCreate(target_id=estate.targets["example.com"], asset_key=fp)
    with pytest.raises(HTTPException) as refused:
        await service.create(estate.user_id, estate.project_id, body)
    assert refused.value.status_code == 404

    await _finding(estate, at=now, fp=fp)
    thread = await service.create(estate.user_id, estate.project_id, body)
    assert thread.title == ask_service.DEFAULT_TITLE
    assert thread.message_count == 0

    with pytest.raises(HTTPException) as other_project:
        await service.create(estate.user_id, uuid.uuid4(), body)
    assert other_project.value.status_code == 404


async def test_threads_are_per_user(ready, estate):
    service = AskService(estate.session)
    other = await _user(estate)
    thread = ready["thread"]
    mine = await service.threads(
        estate.user_id,
        thread.target_id,
        SurfaceDimension.VULNERABILITIES.value,
        ready["fp"],
    )
    assert [t.id for t in mine] == [thread.id]
    assert (
        await service.threads(
            other.id,
            thread.target_id,
            SurfaceDimension.VULNERABILITIES.value,
            ready["fp"],
        )
        == []
    )
    assert await service.get(other.id, thread.id) is None
    assert await service.detail(other.id, thread.id) is None
    assert await service.delete(other.id, thread.id) is False
    assert await service.detail(estate.user_id, thread.id) is not None


async def test_thread_cap_per_finding(ready, estate):
    service = AskService(estate.session)
    body = AskThreadCreate(target_id=ready["thread"].target_id, asset_key=ready["fp"])
    for _ in range(MAX_THREADS_PER_FINDING - 1):
        await service.create(estate.user_id, estate.project_id, body)
    with pytest.raises(HTTPException) as capped:
        await service.create(estate.user_id, estate.project_id, body)
    assert capped.value.status_code == 409


async def test_reply_streams_and_stores_a_cited_answer(ready, estate, monkeypatch):
    seen: dict = {}
    text = "Both came back [F2], on line [R5]. Elsewhere [T1] and [F9] too."
    monkeypatch.setattr(
        ask_service,
        "converse",
        _fake_converse(
            [
                AgentEvent(CALL, name="query_assets", args={"target": "example.com"}),
                AgentEvent(TEXT, text=text[:20]),
                AgentEvent(TEXT, text=text[20:]),
                AgentEvent(
                    DONE, input_tokens=1000, output_tokens=100, model="claude-opus-5"
                ),
            ],
            seen,
        ),
    )
    question = AskQuestion(text="Is it real?", scan_id=estate.scans["run"])
    frames = await _collect(
        reply(
            estate.session,
            thread_id=ready["thread"].id,
            user=ready["user"],
            question=question,
        )
    )

    assert [e for e, _ in frames] == [
        StreamEvent.TRACE.value,
        StreamEvent.TRACE.value,
        StreamEvent.DELTA.value,
        StreamEvent.DELTA.value,
        StreamEvent.DONE.value,
    ]
    assert frames[0][1]["status"] == TraceStatus.RUNNING.value
    assert frames[1][1]["status"] == TraceStatus.DONE.value
    assert frames[1][1]["rows"] == 3
    done = frames[-1][1]
    answer = done["answer"]
    assert (
        answer["text"]
        == "Both came back [[1]], on line [[2]]. Elsewhere [[3]] and too."
    )
    assert [(c["n"], c["kind"]) for c in answer["citations"]] == [
        (1, CitationKind.FACT.value),
        (2, CitationKind.LINE.value),
        (3, CitationKind.TOOL.value),
    ]
    assert answer["citations"][0]["lines"] == [5]
    assert answer["citations"][2]["pivot"].startswith("https://ui/")
    assert answer["input_tokens"] == 1000
    assert answer["cost_usd"] is not None
    assert answer["cost_usd"] > 0
    assert [t["status"] for t in answer["trace"]] == [TraceStatus.DONE.value]
    assert done["question"]["text"] == "Is it real?"
    assert done["thread"]["message_count"] == 2
    assert done["thread"]["title"] == "Is it real?"

    assert "<<untrusted " in seen["system"]
    assert "F1 [for]" in seen["system"]
    assert seen["messages"] == [
        {"role": MessageRole.USER.value, "content": "Is it real?"}
    ]
    assert "query_assets" in seen["tools"]
    assert "list_projects" not in seen["tools"]
    assert seen["tool_text"][0].startswith(
        "T1: Query assets. Cite as [T1].\n<<untrusted "
    )
    assert seen["tool_text"][0].rstrip().endswith(">>")

    stored = await AskService(estate.session).detail(estate.user_id, ready["thread"].id)
    assert [m.role for m in stored.messages] == [
        MessageRole.USER.value,
        MessageRole.ASSISTANT.value,
    ]

    seen.clear()
    monkeypatch.setattr(
        ask_service,
        "converse",
        _fake_converse([AgentEvent(TEXT, text="Again."), AgentEvent(DONE)], seen),
    )
    await _collect(
        reply(
            estate.session,
            thread_id=ready["thread"].id,
            user=ready["user"],
            question=AskQuestion(text="And the fix?", scan_id=estate.scans["run"]),
        )
    )
    assert [m["role"] for m in seen["messages"]] == ["user", "assistant", "user"]
    assert seen["messages"][-1]["content"] == "And the fix?"
    assert "[[" not in seen["messages"][1]["content"]


async def test_reply_refuses_when_ai_is_off(ready, estate, monkeypatch):
    monkeypatch.setattr(ask_service, "load_config_async", _cfg_loader(None))
    frames = await _collect(
        reply(
            estate.session,
            thread_id=ready["thread"].id,
            user=ready["user"],
            question=AskQuestion(text="hi", scan_id=estate.scans["run"]),
        )
    )
    assert frames == [(StreamEvent.ERROR.value, {"message": "AI is switched off."})]
    stored = await AskService(estate.session).detail(estate.user_id, ready["thread"].id)
    assert stored.messages == []


async def test_reply_guards_scan_owner_and_rate(ready, estate, now, monkeypatch):
    other_user = await _user(estate)
    frames = await _collect(
        reply(
            estate.session,
            thread_id=ready["thread"].id,
            user=other_user,
            question=AskQuestion(text="hi", scan_id=estate.scans["run"]),
        )
    )
    assert frames[0][1]["message"] == "Thread not found."

    await estate.scan("example.com", "other", at=now + timedelta(days=1))
    frames = await _collect(
        reply(
            estate.session,
            thread_id=ready["thread"].id,
            user=ready["user"],
            question=AskQuestion(text="hi", scan_id=estate.scans["other"]),
        )
    )
    assert frames[0][1]["message"] == "Finding not found in that scan."

    async def always(token_id, limit):
        return True

    monkeypatch.setattr(ask_service.limits, "exceeded", always)
    frames = await _collect(
        reply(
            estate.session,
            thread_id=ready["thread"].id,
            user=ready["user"],
            question=AskQuestion(text="hi", scan_id=estate.scans["run"]),
        )
    )
    assert frames[0][1]["message"] == "Too many questions. Wait a minute."

    monkeypatch.setattr(ask_service.limits, "exceeded", _never)

    async def over(user_id):
        return True

    monkeypatch.setattr(ask_service.budget, "over_daily", over)
    frames = await _collect(
        reply(
            estate.session,
            thread_id=ready["thread"].id,
            user=ready["user"],
            question=AskQuestion(text="hi", scan_id=estate.scans["run"]),
        )
    )
    assert frames[0][1]["message"].endswith("Ask again tomorrow.")


async def test_reply_stores_nothing_when_the_provider_fails(ready, estate, monkeypatch):
    monkeypatch.setattr(
        ask_service,
        "converse",
        _fake_converse([AgentEvent(TEXT, text="part"), AIError("boom")], {}),
    )
    frames = await _collect(
        reply(
            estate.session,
            thread_id=ready["thread"].id,
            user=ready["user"],
            question=AskQuestion(text="hi", scan_id=estate.scans["run"]),
        )
    )
    assert [e for e, _ in frames] == [StreamEvent.DELTA.value, StreamEvent.ERROR.value]
    assert frames[1][1] == {"message": "boom"}
    stored = await AskService(estate.session).detail(estate.user_id, ready["thread"].id)
    assert stored.messages == []
    assert stored.thread.message_count == 0
    assert stored.thread.title == ask_service.DEFAULT_TITLE

    monkeypatch.setattr(
        ask_service, "converse", _fake_converse([AgentEvent(DONE, model="m")], {})
    )
    frames = await _collect(
        reply(
            estate.session,
            thread_id=ready["thread"].id,
            user=ready["user"],
            question=AskQuestion(text="hi", scan_id=estate.scans["run"]),
        )
    )
    assert frames == [(StreamEvent.ERROR.value, {"message": ask_service.NO_ANSWER})]


async def test_brief_states_the_verdict_and_availability(ready, estate, monkeypatch):
    service = AskService(estate.session)
    brief = await service.brief(estate.scans["run"], ready["vuln_id"])
    assert brief.verdict == Verdict.LIKELY.value
    assert brief.available is True
    assert brief.model == "claude-opus-5"
    assert any(f.lines == [5] for f in brief.facts)

    monkeypatch.setattr(ask_service, "load_config_async", _cfg_loader(None))
    off = await service.brief(estate.scans["run"], ready["vuln_id"])
    assert off.available is False
    assert off.off_reason == "AI is switched off."
    assert off.verdict == brief.verdict

    assert await service.brief(uuid.uuid4(), ready["vuln_id"]) is None
