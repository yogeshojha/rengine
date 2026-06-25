from __future__ import annotations

from sqlalchemy import select

from engines.base import Engine, EngineResult
from engines.host_discovery.config import HostDiscoveryConfig
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.ip_address import IpAddress
from tools.naabu.client import NaabuClient, NaabuError

logger = get_logger(__name__)

_RANGE_TYPES = {TargetType.IP_RANGE.value, TargetType.ASN.value}
_LIVENESS_PORTS = "80,443,22,21,25,53,110,143,3389,3306,8080,8443,8000,8888"


class HostDiscoveryEngine(Engine):
    name = "host_discovery"

    def should_run(self) -> bool:
        if self.ctx.target_type not in _RANGE_TYPES:
            return False
        return HostDiscoveryConfig.from_resolved(self.ctx.resolved).enabled

    def run(self) -> EngineResult:
        self._check_abort()
        cfg = HostDiscoveryConfig.from_resolved(self.ctx.resolved)
        net = self.net_options()
        rows = list(
            self.session.execute(
                select(IpAddress).where(IpAddress.scan_id == self.ctx.scan_id)
            )
            .scalars()
            .all()
        )
        if not rows:
            return EngineResult(counts={"alive": 0})

        try:
            client = NaabuClient(
                ports=_LIVENESS_PORTS,
                rate=cfg.rate,
                concurrency=cfg.threads,
                timeout=cfg.timeout,
                proxy_url=net.proxy_url,
                exclude_cdn=False,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("naabu"),
            )
        except NaabuError:
            logger.warning("naabu unavailable, skipping host discovery")
            return EngineResult(counts={"alive": 0})

        found = client.scan([row.ip for row in rows])
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
        return EngineResult(counts={"alive": alive})
