"""A provider decides why a host is worth a look. One directory each, discovered from disk."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass

from interest.context import InterestContext


@dataclass(frozen=True)
class RawSignal:
    subdomain_id: uuid.UUID
    host: str
    source: str
    key: str
    kind: str
    weight: int
    label: str
    reason: str
    evidence: str | None = None
    rule_id: uuid.UUID | None = None
    model: str | None = None
    prompt_version: str | None = None
    # a booster only counts once something else already flagged the host
    booster: bool = False


class InterestProvider:
    name: str = ""
    source: str = ""
    title: str = ""
    description: str = ""
    requires_ai: bool = False
    order: int = 50

    def available(self, ctx: InterestContext) -> bool:  # noqa: ARG002
        return True

    def evaluate(self, ctx: InterestContext) -> Iterable[RawSignal]:
        raise NotImplementedError
