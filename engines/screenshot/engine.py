from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from engines.base import Engine, EngineResult
from engines.screenshot.config import ScreenshotConfig
from shared.logging import get_logger
from shared.models.http_asset import HttpAsset
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


class ScreenshotEngine(Engine):
    name = "screenshot"

    def should_run(self) -> bool:
        return ScreenshotConfig.from_resolved(self.ctx.resolved).enabled

    def run(self) -> EngineResult:
        self._check_abort()
        cfg = ScreenshotConfig.from_resolved(self.ctx.resolved)
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
            return EngineResult(counts={"screenshots": 0})

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
            return EngineResult(counts={"screenshots": 0})

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
        self.emit_progress(f"captured {captured} screenshots")
        return EngineResult(counts={"screenshots": captured})
