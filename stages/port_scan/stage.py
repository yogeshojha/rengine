from __future__ import annotations

from urllib.parse import urlsplit

from sqlalchemy import delete, select

from shared.enums.scan import Phase
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.subdomain import Subdomain
from shared.utils.datetime import utc_now
from stages.base import Stage, StageResult
from stages.port_scan.config import PortScanConfig
from tools.naabu.client import NaabuClient, NaabuError
from tools.naabu.parser import service_for_port

logger = get_logger(__name__)

_IP_FAMILY = {TargetType.IP.value, TargetType.IP_RANGE.value, TargetType.ASN.value}


class PortScanStage(Stage):
    name = "port_scan"
    title = "Port Scan"
    description = "Find open TCP ports on live hosts."
    phase = Phase.EXPANSION.value
    level = 1
    tools = ("naabu",)
    config_model = PortScanConfig

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg
        net = self.net_options()
        ips = self._target_ips()
        if not ips:
            return StageResult(counts={"open_ports": 0})

        try:
            client = NaabuClient(
                ports=cfg.ports,
                rate=cfg.rate,
                concurrency=cfg.threads,
                timeout=cfg.timeout,
                proxy_url=net.proxy_url,
                exclude_cdn=cfg.exclude_cdn,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("naabu"),
            )
        except NaabuError:
            logger.warning("naabu unavailable, skipping port scan")
            return StageResult(counts={"open_ports": 0})

        found = client.scan(ips)
        self._check_abort()
        count = self._persist(found)
        self.emit_progress(f"found {count} open ports across {len(ips)} hosts")
        return StageResult(counts={"open_ports": count})

    def _target_ips(self) -> list[str]:
        target_type = self.ctx.target_type
        if target_type in _IP_FAMILY:
            rows = (
                self.session.execute(
                    select(IpAddress.ip).where(
                        IpAddress.scan_id == self.ctx.scan_id,
                        IpAddress.is_alive.isnot(False),
                    )
                )
                .scalars()
                .all()
            )
            return list(dict.fromkeys(rows))
        if target_type == TargetType.DOMAIN.value:
            subs = (
                self.session.execute(
                    select(Subdomain).where(
                        Subdomain.scan_id == self.ctx.scan_id,
                        Subdomain.is_excluded.is_(False),
                    )
                )
                .scalars()
                .all()
            )
            ips: set[str] = set()
            for sub in subs:
                if sub.is_wildcard:
                    continue
                ips.update(sub.resolved_ips or [])
            return list(ips)
        if target_type == TargetType.URL.value:
            host = urlsplit(self.ctx.target_value).hostname
            return [host] if host else []
        return []

    def _persist(self, found: list[dict]) -> int:
        self.session.execute(delete(Port).where(Port.scan_id == self.ctx.scan_id))
        now = utc_now()
        seen: set[tuple] = set()
        for item in found:
            key = (item["ip"], item["port"], item["protocol"])
            if key in seen:
                continue
            seen.add(key)
            self.session.add(
                Port(
                    scan_id=self.ctx.scan_id,
                    target_id=self.ctx.target_id,
                    project_id=self.ctx.project_id,
                    ip=item["ip"],
                    number=item["port"],
                    protocol=item["protocol"],
                    state="open",
                    service_name=service_for_port(item["port"]),
                    source="naabu",
                    discovered_at=now,
                )
            )
        self.session.commit()
        return len(seen)
