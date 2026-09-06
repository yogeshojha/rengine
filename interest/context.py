"""What every provider is handed: the scan, its rules, and the estate it sits in."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from functools import cached_property

from sqlalchemy import func, select
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
    webserver: str | None
    is_cdn: bool
    asn: int | None
    asn_org: str | None
    favicon_hash: str | None

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
    def host_total(self) -> int:
        return int(
            self.session.execute(
                select(func.count(Subdomain.id)).where(
                    Subdomain.scan_id == self.scan.id,
                    Subdomain.is_excluded.is_(False),
                )
            ).scalar()
            or 0
        )

    @cached_property
    def live_hosts(self) -> list[HostRow]:
        rows = (
            self.session.execute(
                select(
                    Subdomain.id,
                    Subdomain.name,
                    Subdomain.http_status,
                    Subdomain.page_title,
                    Subdomain.tech,
                    Subdomain.webserver,
                    Subdomain.is_cdn,
                    Subdomain.asn,
                    Subdomain.asn_org,
                    Subdomain.favicon_hash,
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

    def judgeable(self, limit: int = MAX_JUDGE_HOSTS) -> list[HostRow]:
        """Bulk parked pages are one answer, not five hundred, so a shape is sampled not sent whole."""
        seen: dict[tuple, int] = {}
        kept: list[HostRow] = []
        for row in self.live_hosts:
            shape = row.shape
            count = seen.get(shape, 0)
            seen[shape] = count + 1
            if count >= SHAPE_KEEP:
                continue
            kept.append(row)
            if len(kept) >= limit:
                break
        return kept
