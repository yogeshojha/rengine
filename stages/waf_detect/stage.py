from __future__ import annotations

from sqlalchemy import select

from shared.enums.scan import Phase
from shared.logging import get_logger
from shared.models.http_asset import HttpAsset
from stages.base import Stage, StageResult
from stages.waf_detect.config import WafDetectConfig
from tools.wafw00f.client import Wafw00fClient, Wafw00fError

logger = get_logger(__name__)

_MAX_URLS = 500


class WafDetectStage(Stage):
    name = "waf_detect"
    title = "WAF Detection"
    description = "Fingerprint web application firewalls in front of live services."
    phase = Phase.EXPANSION.value
    level = 3
    tools = ("wafw00f",)
    config_model = WafDetectConfig

    def run(self) -> StageResult:
        self._check_abort()
        net = self.net_options()
        rows = list(
            self.session.execute(
                select(HttpAsset).where(HttpAsset.scan_id == self.ctx.scan_id)
            )
            .scalars()
            .all()
        )
        live = [row for row in rows if row.status_code]
        if not live:
            return StageResult(counts={"waf": 0})

        try:
            client = Wafw00fClient(
                proxy_url=net.proxy_url,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("wafw00f"),
            )
        except Wafw00fError:
            logger.warning("wafw00f unavailable, skipping WAF detection")
            return StageResult(counts={"waf": 0})

        by_url = {row.url: row for row in rows}
        wafs = client.detect([row.url for row in live][:_MAX_URLS])
        tagged = 0
        for url, firewall in wafs.items():
            row = by_url.get(url)
            if row is not None:
                row.waf = firewall[:100]
                self.session.add(row)
                tagged += 1
        self.session.commit()
        self.emit_progress(f"flagged {tagged} WAF-protected services")
        return StageResult(counts={"waf": tagged})
