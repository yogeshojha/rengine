from __future__ import annotations

from sqlalchemy import select

from shared.enums.scan import Phase
from shared.logging import get_logger
from shared.models.ip_address import IpAddress
from stages.base import IP_TARGETS, Stage, StageResult
from stages.cdn_check.config import CdnCheckConfig
from tools.cdncheck.client import CdncheckClient, CdncheckError

logger = get_logger(__name__)

_MAX_IPS = 16384


class CdnCheckStage(Stage):
    name = "cdn_check"
    title = "CDN Detection"
    description = "Flag hosts served from a CDN so port scans can skip them."
    phase = Phase.EXPANSION.value
    level = 0
    applies_to = IP_TARGETS
    tools = ("cdncheck",)
    touches_target = False
    config_model = CdnCheckConfig

    def run(self) -> StageResult:
        self._check_abort()
        rows = list(
            self.session.execute(
                select(IpAddress).where(IpAddress.scan_id == self.ctx.scan_id)
            )
            .scalars()
            .all()
        )
        if not rows:
            return StageResult(counts={"cdn": 0})

        by_ip = {row.ip: row for row in rows}
        ips = list(by_ip.keys())[:_MAX_IPS]
        try:
            data = CdncheckClient(
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("cdncheck"),
            ).check(ips)
        except CdncheckError:
            logger.warning("cdncheck unavailable, skipping CDN tagging")
            return StageResult(counts={"cdn": 0})

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
        return StageResult(counts={"cdn": tagged})
