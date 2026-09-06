"""A judgement, clearly labelled as one. It never sees a response body and never fails a scan."""

from __future__ import annotations

import json
from collections.abc import Iterable

from interest.base import InterestProvider, RawSignal
from interest.context import HostRow, InterestContext
from interest.providers.ai.prompt import (
    AI_KINDS,
    BATCH_SIZE,
    CONFIDENCE_SCALE,
    MAX_REASON_CHARS,
    MAX_TECH,
    MAX_TITLE,
    PROMPT_VERSION,
    SYSTEM,
    render,
)
from shared.definitions.ai import AITask
from shared.definitions.interest import (
    MAX_EVIDENCE,
    InterestKind,
    InterestSource,
    coerce_kind,
    kind_weight,
)
from shared.logging import get_logger
from shared.services.ai.cache import narrate
from shared.utils.text import strip_control

logger = get_logger(__name__)

FEATURE = "asset_judgement"
SECONDARY_SCALE = 0.4
MAX_KINDS = 3


def _asset(row: HostRow) -> dict:
    return {
        "host": row.name,
        "status": row.http_status,
        "title": strip_control(row.page_title or "")[:MAX_TITLE],
        "tech": [strip_control(str(t))[:40] for t in (row.tech or [])][:MAX_TECH],
    }


def _payload(text: str) -> list[dict]:
    body = text.strip()
    if body.startswith("```"):
        body = body.split("\n", 1)[-1]
        body = body.rsplit("```", 1)[0]
    start, end = body.find("["), body.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        parsed = json.loads(body[start : end + 1])
    except (ValueError, TypeError):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def _kinds(raw: object) -> list[str]:
    values = raw if isinstance(raw, list) else [raw]
    out: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        kind = coerce_kind(value)
        if kind in AI_KINDS and kind not in out:
            out.append(kind)
    return out[:MAX_KINDS] or [InterestKind.OTHER.value]


class AIProvider(InterestProvider):
    name = "ai"
    source = InterestSource.AI.value
    title = "AI"
    description = (
        "Reads the hostname, status, page title and technology of every responding host "
        "and identifies the ones that merit review. A judgement, not an observation."
    )
    requires_ai = True
    order = 30

    def available(self, ctx: InterestContext) -> bool:
        return ctx.ai is not None and ctx.ai.allows(FEATURE)

    def evaluate(self, ctx: InterestContext) -> Iterable[RawSignal]:
        if not self.available(ctx):
            return
        rows = ctx.judgeable()
        if not rows:
            return
        by_host = {row.name.lower(): row for row in rows}
        for start in range(0, len(rows), BATCH_SIZE):
            batch = rows[start : start + BATCH_SIZE]
            yield from self._batch(ctx, batch, by_host)

    def _batch(
        self, ctx: InterestContext, batch: list[HostRow], by_host: dict[str, HostRow]
    ) -> Iterable[RawSignal]:
        prompt = render([_asset(row) for row in batch])
        answer = narrate(
            ctx.session,
            ctx.ai,
            task=AITask.ASSET_JUDGEMENT.value,
            system=SYSTEM,
            prompt=prompt,
            subject=f"{len(batch)} assets",
            fast=True,
        )
        if not answer:
            return
        allowed = {row.name.lower() for row in batch}
        model = ctx.ai.model_for_task(fast=True)
        for item in _payload(answer):
            host = str(item.get("host") or "").strip().lower()
            # a name the model invented is dropped, never stored
            if host not in allowed:
                continue
            row = by_host.get(host)
            if row is None:
                continue
            reason = strip_control(str(item.get("reason") or ""))[:MAX_REASON_CHARS]
            if not reason:
                continue
            scale = CONFIDENCE_SCALE.get(
                str(item.get("confidence") or "medium").lower(), 0.75
            )
            for index, kind in enumerate(_kinds(item.get("kinds"))):
                base = kind_weight(kind) * scale
                weight = base if index == 0 else base * SECONDARY_SCALE
                yield RawSignal(
                    subdomain_id=row.id,
                    host=row.name,
                    source=InterestSource.AI.value,
                    key=f"ai:{kind}",
                    kind=kind,
                    weight=max(1, round(weight)),
                    label="AI",
                    reason=reason if index == 0 else "",
                    evidence=(row.page_title or "")[:MAX_EVIDENCE] or None,
                    model=model,
                    prompt_version=PROMPT_VERSION,
                )
