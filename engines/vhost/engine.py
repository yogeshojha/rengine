from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from engines.base import Engine, EngineResult
from engines.vhost.config import VhostConfig
from shared.enums.subdomain import SubdomainSource
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.subdomain import Subdomain
from shared.utils.datetime import utc_now
from tools.ffuf.client import FfufClient, FfufError

logger = get_logger(__name__)

_MAX_IPS = 8


class VhostEngine(Engine):
    name = "vhost"

    def should_run(self) -> bool:
        if self.ctx.target_type != TargetType.DOMAIN.value:
            return False
        return VhostConfig.from_resolved(self.ctx.resolved).enabled

    def run(self) -> EngineResult:
        self._check_abort()
        cfg = VhostConfig.from_resolved(self.ctx.resolved)
        if not Path(cfg.wordlist).is_file():
            logger.warning("vhost wordlist missing: %s", cfg.wordlist)
            return EngineResult(counts={"subdomains": 0})

        apex = self.ctx.target_value.strip().lower().rstrip(".")
        ips = self._candidate_ips()
        if not ips:
            return EngineResult(counts={"subdomains": 0})

        net = self.net_options()
        try:
            client = FfufClient(
                wordlist=cfg.wordlist,
                threads=cfg.threads,
                rate=cfg.rate,
                proxy_url=net.proxy_url,
                headers=net.headers,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("ffuf"),
            )
        except FfufError:
            logger.warning("ffuf unavailable, skipping vhost discovery")
            return EngineResult(counts={"subdomains": 0})

        found: dict[str, set[str]] = {}
        for ip in ips:
            self._check_abort()
            for label in client.vhost(ip, apex):
                found.setdefault(f"{label}.{apex}", set()).add(ip)

        count = self._persist(found)
        self.emit_progress(f"discovered {count} virtual hosts")
        return EngineResult(counts={"subdomains": count})

    def _candidate_ips(self) -> list[str]:
        subs = (
            self.session.execute(
                select(Subdomain).where(
                    Subdomain.scan_id == self.ctx.scan_id,
                    Subdomain.is_active.is_(True),
                )
            )
            .scalars()
            .all()
        )
        ips: list[str] = []
        seen: set[str] = set()
        for sub in subs:
            if sub.is_wildcard:
                continue
            for ip in sub.resolved_ips or []:
                if ip not in seen:
                    seen.add(ip)
                    ips.append(ip)
        return ips[:_MAX_IPS]

    def _persist(self, found: dict[str, set[str]]) -> int:
        existing = set(
            self.session.execute(
                select(Subdomain.name).where(Subdomain.scan_id == self.ctx.scan_id)
            )
            .scalars()
            .all()
        )
        now = utc_now()
        added = 0
        for name, ips in found.items():
            if name in existing:
                continue
            self.session.add(
                Subdomain(
                    scan_id=self.ctx.scan_id,
                    target_id=self.ctx.target_id,
                    project_id=self.ctx.project_id,
                    name=name,
                    sources=[SubdomainSource.VHOST.value],
                    resolved_ips=sorted(ips),
                    cname=None,
                    is_active=True,
                    is_wildcard=False,
                    is_excluded=False,
                    discovered_at=now,
                )
            )
            added += 1
        self.session.commit()
        return added
