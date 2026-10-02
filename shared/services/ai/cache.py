"""Prose is cached by what it was written from."""

from __future__ import annotations

import asyncio
import hashlib
import json
from contextlib import suppress
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from shared.definitions.ai import CACHE_VERSION
from shared.logging import get_logger
from shared.models.ai import AiNarrative
from shared.services.ai import ledger
from shared.services.ai.client import AIResult, AIUsage, complete
from shared.services.ai.config import AIConfig
from shared.services.ai.ledger import CallRecord
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


def cache_key(task: str, payload: object, model: str) -> str:
    body = (
        payload
        if isinstance(payload, str)
        else json.dumps(payload, sort_keys=True, default=str)
    )
    digest = hashlib.sha256(
        f"{CACHE_VERSION}|{task}|{model}|{body}".encode(errors="replace")
    )
    return digest.hexdigest()


def lookup(session, task: str, key: str) -> AiNarrative | None:
    row = (
        session.execute(
            select(AiNarrative).where(
                AiNarrative.task == task, AiNarrative.cache_key == key
            )
        )
        .scalars()
        .first()
    )
    if row is not None:
        row.hits += 1
        row.last_used_at = utc_now()
        session.add(row)
    return row


def store(
    session,
    *,
    task: str,
    key: str,
    subject: str,
    result: AIResult,
) -> None:
    row = AiNarrative(
        task=task,
        cache_key=key,
        subject=subject[:300],
        provider=result.provider,
        model=result.model,
        content=result.text,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )
    with suppress(IntegrityError), session.begin_nested():
        session.add(row)
        session.flush()


def narrate(
    session,
    cfg: AIConfig,
    *,
    task: str,
    system: str,
    prompt: str,
    subject: str = "",
    usage: AIUsage | None = None,
    use_cache: bool = True,
) -> str | None:
    """Written prose for one task, or None when AI is off, cold or broken."""
    if not cfg.available:
        return None

    model = cfg.model
    key = cache_key(task, prompt, model)

    if use_cache:
        hit = lookup(session, task, key)
        if hit is not None:
            if usage is not None:
                usage.record(AIResult(hit.content, model, cfg.provider, cached=True))
            ledger.record(
                CallRecord(
                    task=task, provider=cfg.provider, model=model, ok=True, cached=True
                )
            )
            return hit.content

    try:
        result = complete(cfg, system=system, prompt=prompt, task=task)
    except Exception as exc:
        logger.warning("ai narration failed", task=task, error=str(exc)[:200])
        if usage is not None:
            usage.failed(task, exc)
        return None

    if usage is not None:
        usage.record(result)
    if not result.text:
        return None
    if use_cache:
        store(session, task=task, key=key, subject=subject, result=result)
    return result.text


async def narrate_async(
    session: AsyncSession,
    cfg: AIConfig,
    *,
    task: str,
    system: str,
    prompt: str,
    subject: str = "",
) -> str | None:
    """narrate over an AsyncSession."""
    if not cfg.available:
        return None

    model = cfg.model
    key = cache_key(task, prompt, model)

    hit = await session.run_sync(lambda s: lookup(s, task, key))
    if hit is not None:
        ledger.record(
            CallRecord(
                task=task, provider=cfg.provider, model=model, ok=True, cached=True
            )
        )
        return hit.content

    try:
        result = await asyncio.to_thread(
            complete, cfg, system=system, prompt=prompt, task=task
        )
    except Exception as exc:
        logger.warning("ai narration failed", task=task, error=str(exc)[:200])
        return None

    if not result.text:
        return None
    await session.run_sync(
        lambda s: store(s, task=task, key=key, subject=subject, result=result)
    )
    return result.text
