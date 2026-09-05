from __future__ import annotations

from sqlalchemy import select

from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.logging import get_logger
from shared.models.ip_address import IpAddress
from stages.base import RANGE_TARGETS, Stage, StageResult
from stages.host_discovery.config import HostDiscoveryConfig
from tools.naabu.client import NaabuClient, NaabuError, NaabuOptions

logger = get_logger(__name__)

_LIVENESS_PORTS = "80,443,22,21,25,53,110,143,3389,3306,8080,8443,8000,8888"


class HostDiscoveryStage(Stage):
    name = "host_discovery"
    title = "Host Discovery"
    description = "Sweep a netblock for responsive hosts before port scanning."
    phase = Phase.EXPANSION.value
    depends_on = frozenset({"seed_resolution"})
    group = StageGroup.ADDRESSES.value
    role = StageRole.CAPABILITY.value
    produces = frozenset({AssetKind.ADDRESSES.value})
    applies_to = RANGE_TARGETS
    tools = ("naabu",)
    config_model = HostDiscoveryConfig

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg
        net = self.net_options()
        rows = list(
            self.session.execute(
                select(IpAddress).where(IpAddress.scan_id == self.ctx.scan_id)
            )
            .scalars()
            .all()
        )
        if not rows:
            return StageResult(counts={"alive": 0})

        try:
            client = NaabuClient(
                options=NaabuOptions(
                    rate=cfg.rate,
                    concurrency=cfg.threads,
                    timeout=cfg.timeout,
                    proxy_url=net.proxy_url,
                    extra_args=self.ctx.resolved.tool_args("naabu"),
                ),
                recorder=self.ctx.recorder,
            )
        except NaabuError:
            logger.warning("naabu unavailable, skipping host discovery")
            return StageResult(counts={"alive": 0})

        found = client.scan([row.ip for row in rows], ["-p", _LIVENESS_PORTS])
        self._check_abort()
        alive_ips = {item["ip"] for item in found}

        alive = 0
        for row in rows:
            is_alive = row.ip in alive_ips
            if row.is_alive is not is_alive:
                row.is_alive = is_alive
                self.session.add(row)
            if is_alive:
                alive += 1
        self.session.commit()
        self.emit_progress(f"{alive}/{len(rows)} hosts alive")
        return StageResult(counts={"alive": alive})
