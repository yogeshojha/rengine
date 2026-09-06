from __future__ import annotations

from pathlib import Path

from sqlalchemy import select, update

from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
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
    depends_on = frozenset({"origin_probe"})
    group = StageGroup.WEB.value
    role = StageRole.CAPABILITY.value
    consumes = frozenset({AssetKind.HTTP_ASSETS.value})
    tools = ("httpx",)
    config_model = ScreenshotConfig

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg
        net = self.net_options()
        # id + url only: the full row carries the stored response body
        live = self.session.execute(
            select(HttpAsset.id, HttpAsset.url).where(
                HttpAsset.scan_id == self.ctx.scan_id,
                HttpAsset.status_code.isnot(None),
            )
        ).all()
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

        by_url = {url: asset_id for asset_id, url in live}
        selected = [url for _, url in live][:_MAX_TARGETS]
        records, cut_short = client.capture(selected)
        updates = []
        for rec in records:
            path = rec.get("screenshot_path")
            asset_id = by_url.get(rec.get("input")) or by_url.get(rec.get("url"))
            if asset_id is not None and path:
                updates.append(
                    {"id": asset_id, "screenshot_path": _relpath(path)[:500]}
                )
        if updates:
            self.session.execute(update(HttpAsset), updates)
            self.session.commit()
        if self.ctx.target_type == TargetType.DOMAIN.value:
            self._denormalize_to_subdomains()
        self.emit_progress(f"captured {len(updates)} screenshots")
        skipped = max(0, len(live) - len(selected))
        warnings = []
        if cut_short:
            warnings.append(
                f"the renderer ran out of time. {len(updates):,} of "
                f"{len(selected):,} services were captured."
            )
        if skipped:
            warnings.append(
                f"{skipped:,} services beyond the {_MAX_TARGETS:,} budget were not captured"
            )
        return StageResult(
            counts={"screenshots": len(updates)},
            warnings=warnings,
            partial=bool(warnings),
        )

    def _denormalize_to_subdomains(self) -> None:
        shots = dict(
            self.session.execute(
                select(HttpAsset.url, HttpAsset.screenshot_path).where(
                    HttpAsset.scan_id == self.ctx.scan_id,
                    HttpAsset.screenshot_path.isnot(None),
                )
            ).all()
        )
        if not shots:
            return
        rows = self.session.execute(
            select(Subdomain.id, Subdomain.http_url).where(
                Subdomain.scan_id == self.ctx.scan_id,
                Subdomain.http_url.isnot(None),
            )
        ).all()
        updates = [
            {"id": sub_id, "screenshot_path": shots[url]}
            for sub_id, url in rows
            if url in shots
        ]
        if updates:
            self.session.execute(update(Subdomain), updates)
            self.session.commit()
