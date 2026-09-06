from __future__ import annotations

import ipaddress

from sqlalchemy import select

from shared.definitions.rescan import SeedKind
from shared.enums.ip import IpSource
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.services import ip_inventory
from shared.utils.datetime import utc_now
from stages.asset_seed.config import AssetSeedConfig
from stages.base import ALL_TARGETS, Stage, StageResult

logger = get_logger(__name__)

_SEED_SOURCE = "rescan"


class AssetSeedStage(Stage):
    name = "asset_seed"
    title = "Seed Assets"
    description = "Start a focused scan from assets chosen in an earlier run."
    phase = Phase.DISCOVERY.value
    group = StageGroup.HOSTS.value
    role = StageRole.SUPPORT.value
    produces = frozenset({AssetKind.HOSTS.value, AssetKind.ADDRESSES.value})
    applies_to = ALL_TARGETS
    touches_target = False
    catalog_hidden = True
    config_model = AssetSeedConfig

    def run(self) -> StageResult:
        self._check_abort()
        hosts, addresses = self._seeds()
        if not hosts and not addresses:
            return StageResult(
                counts={},
                warnings=["No assets were seeded for this run."],
                partial=True,
            )

        carried = self._carried(hosts)
        stored = self._persist_hosts(hosts, carried)
        addresses = list(
            dict.fromkeys(addresses + [ip for ips in carried.values() for ip in ips])
        )
        materialized = ip_inventory.materialize(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            ips=addresses,
            source=IpSource.SEED.value,
        )
        self.session.commit()
        self.emit_progress(f"seeded {stored} host(s) and {materialized} address(es)")
        return StageResult(counts={"subdomains": stored, "ips": materialized})

    def _seeds(self) -> tuple[list[str], list[str]]:
        hosts: list[str] = []
        addresses: list[str] = []
        for seed in self.ctx.resolved.seed_assets or []:
            value = (seed.get("value") or "").strip()
            if not value:
                continue
            if seed.get("kind") == SeedKind.ADDRESS.value:
                try:
                    ipaddress.ip_address(value)
                except ValueError:
                    logger.warning("invalid address seed: %s", value)
                    continue
                addresses.append(value)
            else:
                hosts.append(value.lower())
        return list(dict.fromkeys(hosts)), list(dict.fromkeys(addresses))

    def _carried(self, hosts: list[str]) -> dict[str, list[str]]:
        """Resolved addresses the parent run already knew, so downstream stages are fed."""
        if not hosts:
            return {}
        parent = self.session.execute(
            select(Scan.parent_scan_id).where(Scan.id == self.ctx.scan_id)
        ).scalar_one_or_none()
        if parent is None:
            return {}
        rows = self.session.execute(
            select(Subdomain.name, Subdomain.resolved_ips, Subdomain.cname).where(
                Subdomain.scan_id == parent, Subdomain.name.in_(hosts)
            )
        ).all()
        self._cnames = {name: cname for name, _, cname in rows if cname}
        return {name: list(ips or []) for name, ips, _ in rows}

    def _persist_hosts(self, hosts: list[str], carried: dict[str, list[str]]) -> int:
        if not hosts:
            return 0
        now = utc_now()
        cnames = getattr(self, "_cnames", {})
        self.session.add_all(
            [
                Subdomain(
                    scan_id=self.ctx.scan_id,
                    target_id=self.ctx.target_id,
                    project_id=self.ctx.project_id,
                    name=name,
                    sources=[_SEED_SOURCE],
                    resolved_ips=carried.get(name, []),
                    cname=cnames.get(name),
                    is_active=True,
                    discovered_at=now,
                )
                for name in hosts
            ]
        )
        return len(hosts)
