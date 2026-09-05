from __future__ import annotations

import ipaddress

from sqlalchemy import select

from shared.definitions.ports import PortSource
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.logging import get_logger
from shared.models.ip_address import IpAddress
from shared.services import ip_inventory, port_inventory
from shared.services.port_inventory import ServiceObservation
from shared.services.scope_filter import ip_excluded
from stages.base import ALL_TARGETS, Stage, StageResult
from stages.passive_ports.config import PassivePortsConfig
from tools.naabu.client import NaabuClient, NaabuError, NaabuOptions

logger = get_logger(__name__)


class PassivePortsStage(Stage):
    name = "passive_ports"
    title = "Passive Port Discovery"
    description = (
        "Read ports already indexed for each address by internet-wide scanners."
    )
    phase = Phase.EXPANSION.value
    depends_on = frozenset({"host_discovery", "seed_resolution", "subdomain_discovery"})
    group = StageGroup.SERVICES.value
    role = StageRole.SUPPORT.value
    consumes = frozenset({AssetKind.ADDRESSES.value})
    produces = frozenset({AssetKind.PORTS.value})
    applies_to = ALL_TARGETS
    tools = ("naabu",)
    touches_target = False
    config_model = PassivePortsConfig

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg
        ip_inventory.ensure(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
        )
        addresses = self._candidates(cfg.max_addresses)
        if not addresses:
            return StageResult(counts={"known_ports": 0, "addresses": 0})

        try:
            client = NaabuClient(
                options=NaabuOptions(
                    extra_args=self.ctx.resolved.tool_args("naabu"),
                ),
                recorder=self.ctx.recorder,
            )
        except NaabuError:
            logger.warning("naabu unavailable, skipping passive port lookup")
            return StageResult(counts={"known_ports": 0, "addresses": 0})

        try:
            found = client.passive(addresses)
        except NaabuError as exc:
            # supplementary intel: a failed lookup must not fail the scan, but it must be visible
            logger.warning("passive port lookup failed: %s", exc)
            self.emit_progress(f"passive lookup failed: {exc}")
            return StageResult(counts={"known_ports": 0, "addresses": len(addresses)})
        self._check_abort()
        count = port_inventory.upsert(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            source=PortSource.INTERNETDB.value,
            observations=[
                ServiceObservation(
                    ip=item["ip"],
                    port=item["port"],
                    protocol=item["protocol"],
                    tls=item["tls"],
                )
                for item in found
            ],
        )
        self.emit_progress(
            f"{count} ports already indexed across {len(addresses)} addresses"
        )
        return StageResult(counts={"known_ports": count, "addresses": len(addresses)})

    def _candidates(self, budget: int) -> list[str]:
        excluded = self.ctx.resolved.excluded_ips or []
        rows = (
            self.session.execute(
                select(IpAddress.ip).where(IpAddress.scan_id == self.ctx.scan_id)
            )
            .scalars()
            .all()
        )
        out: list[str] = []
        for ip in dict.fromkeys(rows):
            try:
                if not ipaddress.ip_address(ip).is_global:
                    continue
            except ValueError:
                continue
            if excluded and ip_excluded(ip, excluded):
                continue
            out.append(ip)
            if len(out) >= budget:
                break
        return out
