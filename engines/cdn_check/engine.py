from __future__ import annotations

from sqlalchemy import select

from engines.base import Engine, EngineResult
from engines.cdn_check.config import CdnCheckConfig
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.ip_address import IpAddress
from tools.cdncheck.client import CdncheckClient, CdncheckError

logger = get_logger(__name__)

_IP_FAMILY = {TargetType.IP.value, TargetType.IP_RANGE.value, TargetType.ASN.value}
_MAX_IPS = 16384


class CdnCheckEngine(Engine):
    name = "cdn_check"

    def should_run(self) -> bool:
        if self.ctx.target_type not in _IP_FAMILY:
            return False
        return CdnCheckConfig.from_resolved(self.ctx.resolved).enabled

    def run(self) -> EngineResult:
        self._check_abort()
        rows = list(
            self.session.execute(
                select(IpAddress).where(IpAddress.scan_id == self.ctx.scan_id)
            )
            .scalars()
            .all()
        )
        if not rows:
            return EngineResult(counts={"cdn": 0})

        by_ip = {row.ip: row for row in rows}
        ips = list(by_ip.keys())[:_MAX_IPS]
        try:
            data = CdncheckClient(
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("cdncheck"),
            ).check(ips)
        except CdncheckError:
            logger.warning("cdncheck unavailable, skipping CDN tagging")
            return EngineResult(counts={"cdn": 0})

        tagged = 0
        for ip, info in data.items():
            row = by_ip.get(ip)
            if row is not None and info.get("is_cdn"):
                row.is_cdn = True
                name = info.get("cdn_name")
                row.cdn_name = name[:100] if name else None
                self.session.add(row)
                tagged += 1
        self.session.commit()
        self.emit_progress(f"flagged {tagged} CDN/WAF/cloud IPs")
        return EngineResult(counts={"cdn": tagged})
