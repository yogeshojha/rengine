from __future__ import annotations

from sqlalchemy import select

from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.logging import get_logger
from shared.models.ip_address import IpAddress
from shared.services import ip_inventory
from stages.base import ALL_TARGETS, Stage, StageResult
from stages.cdn_check.config import CdnCheckConfig
from tools.cdncheck.client import CdncheckClient, CdncheckError

logger = get_logger(__name__)

_MAX_IPS = 16384
_CDN_KINDS = ("cdn", "waf")


class CdnCheckStage(Stage):
    name = "cdn_check"
    title = "CDN and Cloud Attribution"
    description = (
        "Identify which addresses are fronted by a CDN, WAF or cloud provider."
    )
    phase = Phase.EXPANSION.value
    level = 1
    group = StageGroup.ADDRESSES.value
    role = StageRole.SUPPORT.value
    consumes = frozenset({AssetKind.ADDRESSES.value})
    applies_to = ALL_TARGETS
    tools = ("cdncheck",)
    touches_target = False
    config_model = CdnCheckConfig

    def run(self) -> StageResult:
        self._check_abort()
        ips = ip_inventory.ensure(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
        )
        if not ips:
            return StageResult(counts={"addresses": 0, "cdn": 0, "cloud": 0})

        try:
            data = CdncheckClient(
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("cdncheck"),
            ).check(ips[:_MAX_IPS])
        except CdncheckError:
            logger.warning("cdncheck unavailable, skipping CDN attribution")
            return StageResult(counts={"addresses": len(ips), "cdn": 0, "cloud": 0})

        self._check_abort()
        rows = {
            row.ip: row
            for row in self.session.execute(
                select(IpAddress).where(IpAddress.scan_id == self.ctx.scan_id)
            )
            .scalars()
            .all()
        }
        cdn = cloud = 0
        for ip, info in data.items():
            row = rows.get(ip)
            if row is None or not info.get("is_cdn"):
                continue
            kind = info.get("cdn_type") or "cdn"
            name = info.get("cdn_name")
            row.cdn_type = kind
            row.cdn_name = name[:100] if name else None
            row.is_cdn = kind in _CDN_KINDS
            self.session.add(row)
            if row.is_cdn:
                cdn += 1
            else:
                cloud += 1
        self.session.commit()
        self.emit_progress(
            f"{cdn} of {len(ips)} addresses fronted by a CDN or WAF, {cloud} on cloud infrastructure"
        )
        return StageResult(counts={"addresses": len(ips), "cdn": cdn, "cloud": cloud})
