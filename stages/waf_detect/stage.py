from __future__ import annotations

from sqlalchemy import select, update

from shared.definitions.intensity import TransportTool
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
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
    description = "Fingerprint web application firewalls in front of live web assets."
    phase = Phase.EXPANSION.value
    depends_on = frozenset({"http_probe"})
    group = StageGroup.WEB.value
    role = StageRole.SUPPORT.value
    consumes = frozenset({AssetKind.HTTP_ASSETS.value})
    tools = ("wafw00f",)
    transport_tool = TransportTool.HTTPX.value
    thread_weight = 1 / 25
    config_model = WafDetectConfig

    def run(self) -> StageResult:
        self._check_abort()
        net = self.net_options()
        live = self.session.execute(
            select(HttpAsset.id, HttpAsset.url).where(
                HttpAsset.scan_id == self.ctx.scan_id,
                HttpAsset.status_code.isnot(None),
            )
        ).all()
        if not live:
            return StageResult(counts={"waf": 0})

        try:
            client = Wafw00fClient(
                proxy_url=net.proxy_url,
                headers=net.headers,
                concurrency=self.transport.threads,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("wafw00f"),
            )
        except Wafw00fError as exc:
            logger.warning("wafw00f unavailable, skipping WAF detection")
            return StageResult(counts={"waf": 0}, warnings=[str(exc)], partial=True)

        by_url = {url: asset_id for asset_id, url in live}
        scan = client.detect([url for _, url in live][:_MAX_URLS])
        updates = [
            {"id": by_url[url], "waf": firewall[:100]}
            for url, firewall in scan.found.items()
            if url in by_url
        ]
        if updates:
            self.session.execute(update(HttpAsset), updates)
            self.session.commit()
        self.emit_progress(f"{len(updates)} web assets behind a WAF")
        skipped = max(0, len(live) - _MAX_URLS)
        warnings = []
        if client.unreadable_headers:
            names = ", ".join(client.unreadable_headers)
            warnings.append(
                f"{names} not sent to wafw00f. A header value holding a colon is "
                "unreadable by wafw00f."
            )
        if scan.unfinished:
            warnings.append(
                f"wafw00f did not finish {scan.unfinished:,} of "
                f"{scan.scanned + scan.unfinished:,} web assets."
            )
        if skipped:
            warnings.append(
                f"{skipped:,} web assets not checked. Limit is {_MAX_URLS:,} per scan."
            )
        return StageResult(
            counts={"waf": len(updates), "checked": scan.scanned},
            warnings=warnings,
            partial=bool(warnings),
        )
