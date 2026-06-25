from __future__ import annotations

from sqlalchemy import select

from engines.base import Engine, EngineResult
from engines.reverse_dns.config import ReverseDnsConfig
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.ip_address import IpAddress
from tools.dnsx.client import DnsxClient, DnsxError
from tools.dnsx.parser import parse_dnsx_jsonl

logger = get_logger(__name__)

_IP_FAMILY = {TargetType.IP.value, TargetType.IP_RANGE.value, TargetType.ASN.value}
_MAX_PTR = 8192


class ReverseDnsEngine(Engine):
    name = "reverse_dns"

    def should_run(self) -> bool:
        if self.ctx.target_type not in _IP_FAMILY:
            return False
        return ReverseDnsConfig.from_resolved(self.ctx.resolved).enabled

    def run(self) -> EngineResult:
        self._check_abort()
        cfg = ReverseDnsConfig.from_resolved(self.ctx.resolved)
        rows = list(
            self.session.execute(
                select(IpAddress).where(IpAddress.scan_id == self.ctx.scan_id)
            )
            .scalars()
            .all()
        )
        if not rows:
            return EngineResult(counts={"ptr": 0})

        by_ip = {row.ip: row for row in rows}
        ips = list(by_ip.keys())[:_MAX_PTR]
        ptr_map = self._lookup_ptr(ips, cfg)

        resolved = 0
        for ip, names in ptr_map.items():
            row = by_ip.get(ip)
            if row is not None and names:
                row.ptr_hostnames = names
                self.session.add(row)
                resolved += 1
        self.session.commit()
        self.emit_progress(f"reverse-DNS resolved {resolved}/{len(ips)} IPs")
        return EngineResult(counts={"ptr": resolved})

    def _lookup_ptr(self, ips: list[str], cfg: ReverseDnsConfig) -> dict[str, list]:
        if not ips:
            return {}
        try:
            client = DnsxClient(
                timeout=max(120, cfg.dns_timeout),
                threads=cfg.dns_threads,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("dnsx"),
            )
        except DnsxError:
            logger.warning("dnsx unavailable, skipping reverse DNS")
            return {}

        result = client.ptr(ips)
        out: dict[str, list] = {}
        for rec in parse_dnsx_jsonl(result.json_records):
            if rec.ptr:
                out[rec.host] = list(rec.ptr)
        return out
