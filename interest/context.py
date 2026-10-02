from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from functools import cached_property

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.models.interest import InterestRule
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.services.ai.config import AIConfig
from shared.utils.datetime import utc_now

MAX_JUDGE_HOSTS = 1500
SHAPE_KEEP = 3


@dataclass
class HostRow:
    id: object
    name: str
    http_status: int | None
    page_title: str | None
    tech: list

    @property
    def shape(self) -> tuple:
        return (
            self.http_status,
            (self.page_title or "").strip().lower()[:120],
            tuple(sorted(t.lower() for t in (self.tech or []))[:6]),
        )


@dataclass
class InterestContext:
    session: Session
    scan: Scan
    rules: list[InterestRule] = field(default_factory=list)
    ai: AIConfig | None = None
    now: datetime = field(default_factory=utc_now)

    @cached_property
    def answered_hosts(self) -> list[HostRow]:
        rows = (
            self.session.execute(
                select(
                    Subdomain.id,
                    Subdomain.name,
                    Subdomain.http_status,
                    Subdomain.page_title,
                    Subdomain.tech,
                )
                .where(
                    Subdomain.scan_id == self.scan.id,
                    Subdomain.is_excluded.is_(False),
                    Subdomain.http_status.isnot(None),
                )
                .order_by(Subdomain.name)
            )
            .mappings()
            .all()
        )
        return [HostRow(**dict(r)) for r in rows]

    def judgeable(self) -> list[HostRow]:
        """Answered hosts, at most SHAPE_KEEP per response shape."""
        seen: dict[tuple, int] = {}
        kept: list[HostRow] = []
        for row in self.answered_hosts:
            shape = row.shape
            count = seen.get(shape, 0)
            seen[shape] = count + 1
            if count >= SHAPE_KEEP:
                continue
            kept.append(row)
            if len(kept) >= MAX_JUDGE_HOSTS:
                break
        return kept
