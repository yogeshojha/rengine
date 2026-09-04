from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from shared.enums.scan import Phase
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.http_asset import HttpAsset
from shared.models.subdomain import Subdomain
from stages.base import Stage, StageResult
from stages.screenshot.config import ScreenshotConfig
from tools.httpx.client import HttpxClient, HttpxError

logger = get_logger(__name__)

_MEDIA_ROOT = "/app/scan_media"
_MAX_TARGETS = 2000


def _relpath(path: str) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        return path
    try:
        return str(candidate.relative_to(_MEDIA_ROOT))
    except ValueError:
        return path


class ScreenshotStage(Stage):
    name = "screenshot"
    title = "Screenshots"
    description = "Render every live HTTP service to an image."
    phase = Phase.EXPANSION.value
    level = 5
    tools = ("httpx",)
    config_model = ScreenshotConfig

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg
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
            return StageResult(counts={"screenshots": 0})

        store_dir = str(Path(_MEDIA_ROOT) / str(self.ctx.scan_id))
        try:
            client = HttpxClient(
                threads=cfg.threads,
                timeout=cfg.timeout,
                proxy_url=net.proxy_url,
                headers=net.headers,
                store_dir=store_dir,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("httpx"),
            )
        except HttpxError:
            logger.warning("httpx unavailable, skipping screenshots")
            return StageResult(counts={"screenshots": 0})

        by_url = {row.url: row for row in rows}
        records = client.capture([row.url for row in live][:_MAX_TARGETS])
        captured = 0
        for rec in records:
            path = rec.get("screenshot_path")
            row = by_url.get(rec.get("input")) or by_url.get(rec.get("url"))
            if row is not None and path:
                row.screenshot_path = _relpath(path)[:500]
                self.session.add(row)
                captured += 1
        self.session.commit()
        if self.ctx.target_type == TargetType.DOMAIN.value:
            self._denormalize_to_subdomains()
        self.emit_progress(f"captured {captured} screenshots")
        return StageResult(counts={"screenshots": captured})

    def _denormalize_to_subdomains(self) -> None:
        shots = {
            asset.url: asset.screenshot_path
            for asset in self.session.execute(
                select(HttpAsset).where(HttpAsset.scan_id == self.ctx.scan_id)
            )
            .scalars()
            .all()
            if asset.screenshot_path
        }
        subs = (
            self.session.execute(
                select(Subdomain).where(
                    Subdomain.scan_id == self.ctx.scan_id,
                    Subdomain.http_url.isnot(None),
                )
            )
            .scalars()
            .all()
        )
        changed = 0
        for sub in subs:
            path = shots.get(sub.http_url)
            if path:
                sub.screenshot_path = path
                self.session.add(sub)
                changed += 1
        if changed:
            self.session.commit()
