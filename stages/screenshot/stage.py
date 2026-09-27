from __future__ import annotations

import contextlib
from pathlib import Path

from sqlalchemy import select, update

from shared.definitions.intensity import TransportTool
from shared.definitions.surface import SurfaceDimension
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.http_asset import HttpAsset
from shared.models.subdomain import Subdomain
from shared.utils.imagehash import phash_file
from shared.utils.validation import validate_ip
from stages.base import Stage, StageResult
from stages.screenshot.config import ScreenshotConfig
from tools.httpx.client import HttpxClient, HttpxError

logger = get_logger(__name__)

_MEDIA_ROOT = "/app/scan_media"
_MAX_TARGETS = 6000
_WRITE_BATCH = 50


def _relpath(path: str) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        return path
    try:
        return str(candidate.relative_to(_MEDIA_ROOT))
    except ValueError:
        return path


def _is_ip(host: str | None) -> bool:
    return validate_ip((host or "").strip("[]"))


_STATUS_RANK: tuple[tuple[range, int], ...] = (
    (range(200, 300), 0),
    (range(300, 400), 1),
    (range(401, 404), 2),
    (range(404, 405), 3),
    (range(400, 500), 4),
    (range(500, 600), 5),
)


def _status_rank(status: int | None) -> int:
    if status is None:
        return 6
    for span, rank in _STATUS_RANK:
        if status in span:
            return rank
    return 6


def _rank(row) -> tuple:
    """Rank web assets: answering, hostname, https, then the value."""
    _id, url, host, scheme, status = row
    return (
        _status_rank(status),
        1 if _is_ip(host) else 0,
        0 if scheme == "https" else 1,
        url or "",
    )


class ScreenshotStage(Stage):
    name = "screenshot"
    title = "Screenshots"
    description = "Render live web assets to images."
    phase = Phase.EXPANSION.value
    depends_on = frozenset({"origin_probe"})
    group = StageGroup.WEB.value
    role = StageRole.CAPABILITY.value
    consumes = frozenset({AssetKind.HTTP_ASSETS.value})
    tools = ("httpx",)
    transport_tool = TransportTool.HTTPX.value
    thread_weight = 4 / 15
    config_model = ScreenshotConfig

    def run(self) -> StageResult:
        self._check_abort()
        net = self.net_options()
        live = self.session.execute(
            select(
                HttpAsset.id,
                HttpAsset.url,
                HttpAsset.host,
                HttpAsset.scheme,
                HttpAsset.status_code,
            ).where(
                HttpAsset.scan_id == self.ctx.scan_id,
                HttpAsset.status_code.isnot(None),
            )
        ).all()
        if not live:
            return StageResult(counts={"screenshots": 0})

        store_dir = str(Path(_MEDIA_ROOT) / str(self.ctx.scan_id))
        try:
            client = HttpxClient(
                rate_limit=self.transport.rate,
                threads=self.transport.threads,
                timeout=self.transport.timeout,
                proxy_url=net.proxy_url,
                headers=net.headers,
                probe_scheme=net.probe_scheme,
                follow_redirects=self.follow_redirects(True),
                store_dir=store_dir,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("httpx"),
            )
        except HttpxError as exc:
            logger.warning("httpx unavailable, skipping screenshots")
            return StageResult(warnings=[str(exc)], partial=True)

        ranked = sorted(live, key=_rank)
        chosen = ranked[:_MAX_TARGETS]
        by_url = {row[1]: row[0] for row in chosen}
        selected = [row[1] for row in chosen]

        def _write(batch: list[dict]) -> int:
            self.session.execute(update(HttpAsset), batch)
            self.session.commit()
            return len(batch)

        sink = self.results_sink(
            SurfaceDimension.WEB_ASSETS.value, _write, rows=_WRITE_BATCH
        )
        captured, answered, failed, cut_short = self._capture(
            client, selected, by_url, sink
        )
        if self.ctx.target_type == TargetType.DOMAIN.value:
            self._denormalize_to_subdomains()
        self.emit_progress(f"captured {captured} screenshots")
        no_answer = max(0, len(selected) - answered)
        skipped = max(0, len(ranked) - len(chosen))
        warnings = []
        if cut_short:
            warnings.append(
                f"the renderer ran out of time. {captured:,} of "
                f"{len(selected):,} web assets were captured."
            )
        if failed:
            warnings.append(f"{failed:,} web assets did not render an image")
        if no_answer:
            warnings.append(f"{no_answer:,} web assets did not answer during capture")
        if skipped:
            warnings.append(
                f"{skipped:,} web assets beyond the {_MAX_TARGETS:,} budget were not captured"
            )
        return StageResult(
            counts={"screenshots": captured},
            warnings=warnings,
            partial=bool(warnings),
        )

    def _capture(self, client, selected, by_url, sink) -> tuple[int, int, int, bool]:
        """Render each chosen web asset, keeping only readable images."""
        captured = answered = failed = 0
        with client.stream_capture(selected) as stream:
            for rec in stream.records:
                answered += 1
                path = rec.get("screenshot_path")
                asset_id = by_url.get(rec.get("input")) or by_url.get(rec.get("url"))
                if asset_id is None or not path:
                    continue
                phash = phash_file(path)
                if phash is None:
                    failed += 1
                    with contextlib.suppress(OSError):
                        Path(path).unlink(missing_ok=True)
                    continue
                captured += 1
                sink.add(
                    {
                        "id": asset_id,
                        "screenshot_path": _relpath(path)[:500],
                        "screenshot_phash": phash,
                    }
                )
                if sink.pending == 0:
                    self._check_abort()
        sink.close()
        return captured, answered, failed, stream.timed_out

    def _denormalize_to_subdomains(self) -> None:
        shots: dict[str, tuple] = {}
        for host, path, phash in self.session.execute(
            select(
                HttpAsset.host,
                HttpAsset.screenshot_path,
                HttpAsset.screenshot_phash,
            )
            .where(
                HttpAsset.scan_id == self.ctx.scan_id,
                HttpAsset.screenshot_path.isnot(None),
            )
            .order_by(HttpAsset.scheme.desc(), HttpAsset.status_code)
        ).all():
            shots.setdefault(host, (path, phash))
        if not shots:
            return
        rows = self.session.execute(
            select(Subdomain.id, Subdomain.name).where(
                Subdomain.scan_id == self.ctx.scan_id,
                Subdomain.name.in_(list(shots)),
            )
        ).all()
        updates = [
            {
                "id": sub_id,
                "screenshot_path": shots[name][0],
                "screenshot_phash": shots[name][1],
            }
            for sub_id, name in rows
            if name in shots
        ]
        if updates:
            self.session.execute(update(Subdomain), updates)
            self.session.commit()
