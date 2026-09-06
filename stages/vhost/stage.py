from __future__ import annotations

from sqlalchemy import select

from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.enums.subdomain import SubdomainSource
from shared.logging import get_logger
from shared.models.subdomain import Subdomain
from shared.services.wordlists import WordlistError, lookup, resolve_path
from shared.utils.datetime import utc_now
from stages.base import DOMAIN_TARGETS, Stage, StageResult
from stages.vhost.config import VhostConfig
from tools.ffuf.client import FfufClient, FfufError

logger = get_logger(__name__)

_MAX_IPS = 8


class VhostStage(Stage):
    name = "vhost"
    title = "Virtual Host Discovery"
    description = "Find virtual hosts that DNS does not resolve, by varying the Host header."
    phase = Phase.EXPANSION.value
    depends_on = frozenset({"reverse_dns", "subdomain_discovery"})
    group = StageGroup.HOSTS.value
    role = StageRole.CAPABILITY.value
    consumes = frozenset({AssetKind.HOSTS.value})
    produces = frozenset({AssetKind.HOSTS.value})
    applies_to = DOMAIN_TARGETS
    tools = ("ffuf",)
    config_model = VhostConfig

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg
        row = lookup(self.session, cfg.wordlist)
        if row is None:
            logger.warning("vhost wordlist not in the library: %s", cfg.wordlist)
            return StageResult(
                counts={"subdomains": 0},
                warnings=[f"No wordlist named {cfg.wordlist!r} is in the library"],
                partial=True,
            )
        try:
            wordlist = resolve_path(row)
        except WordlistError as exc:
            return StageResult(
                counts={"subdomains": 0}, warnings=[str(exc)], partial=True
            )
        if not wordlist.is_file():
            return StageResult(
                counts={"subdomains": 0},
                warnings=[f"{row.name} is in the library but its file is missing"],
                partial=True,
            )

        apex = self.ctx.target_value.strip().lower().rstrip(".")
        ips = self._candidate_ips()
        if not ips:
            return StageResult(counts={"subdomains": 0})

        net = self.net_options()
        try:
            client = FfufClient(
                wordlist=str(wordlist),
                threads=cfg.threads,
                rate=cfg.rate,
                proxy_url=net.proxy_url,
                headers=net.headers,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("ffuf"),
            )
        except FfufError:
            logger.warning("ffuf unavailable, skipping vhost discovery")
            return StageResult(counts={"subdomains": 0})

        found: dict[str, set[str]] = {}
        for ip in ips:
            self._check_abort()
            for label in client.vhost(ip, apex):
                found.setdefault(f"{label}.{apex}", set()).add(ip)

        count = self._persist(found)
        self.emit_progress(f"discovered {count} virtual hosts")
        return StageResult(counts={"subdomains": count})

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
