"""Prose is cached by what it was written from, so a re-run of the same report costs nothing."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from shared.definitions.ai import CACHE_VERSION, GLOBAL_CACHE_TASKS
from shared.logging import get_logger
from shared.models.ai import AiNarrative
from shared.services.ai.client import AIError, AIResult, AIUsage, complete
from shared.services.ai.config import AIConfig
from shared.utils.datetime import utc_now

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
    session.add(row)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()


def narrate(
    session,
    cfg: AIConfig,
    *,
    task: str,
    system: str,
    prompt: str,
    subject: str = "",
    fast: bool = False,
    usage: AIUsage | None = None,
    use_cache: bool = True,
) -> str | None:
    """Written prose for one task, or None when AI is off, cold or broken."""
    if not cfg.available:
        return None

    model = cfg.model_for_task(fast=fast)
    key = cache_key(task, prompt, model)

    if use_cache:
        hit = lookup(session, task, key)
        if hit is not None:
            if usage is not None:
                usage.record(AIResult(hit.content, model, cfg.provider, cached=True))
            return hit.content

    try:
        result = complete(cfg, system=system, prompt=prompt, task=task, fast=fast)
    except (AIError, Exception) as exc:
        logger.warning("ai narration failed", task=task, error=str(exc)[:200])
        if usage is not None:
            usage.failures.append(f"{task}: {exc}"[:300])
        return None

    if not result.text:
        return None
    if usage is not None:
        usage.record(result)
    if use_cache:
        store(session, task=task, key=key, subject=subject, result=result)
    return result.text


def cached_count(session) -> int:
    return int(session.execute(select(func.count(AiNarrative.id))).scalar() or 0)


def is_globally_cached(task: str) -> bool:
    return task in GLOBAL_CACHE_TASKS
