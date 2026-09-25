from __future__ import annotations

import time
from collections import deque
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select

from shared.definitions.ai_services import (
    AI_PORTS,
    MCP_PATHS,
    MCP_SERVICE,
    REQUESTS_PER_ASSET,
)
from shared.definitions.intensity import TransportTool
from shared.definitions.ports import DEFAULT_WEB_PORTS
from shared.definitions.surface import SurfaceDimension
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.logging import get_logger
from shared.models.http_asset import HttpAsset
from shared.services import ai_services
from shared.services.ai_services import Detection
from shared.utils.net import host_port
from shared.utils.text import counted
from stages.ai_detection.config import (
    BATCH_ASSETS,
    BATCH_SECONDS_PER_ASSET,
    JULIUS_CONCURRENCY,
    AiDetectionConfig,
)
from stages.base import ALL_TARGETS, Stage, StageResult
from tools.julius import JuliusClient, JuliusError, JuliusOptions, JuliusRun
from tools.julius.client import MCP_PROBES_DIR
from tools.runner.abort import StageAbortedError

logger = get_logger(__name__)

_POLL_SECONDS = 1.0
_MCP_REQUESTS = 1


@dataclass
class _Root:
    url: str
    host: str
    port: int
    assets: list[UUID] = field(default_factory=list)


@dataclass
class _Batch:
    targets: list[str]
    roots: dict[str, _Root]
    cost: int
    mcp: bool = False


class _Pacer:
    """Spaces batch starts so the stage averages no more than its rate."""

    def __init__(self, rate: int | None) -> None:
        self.rate = rate
        self.next_at = time.monotonic()

    def wait_seconds(self) -> float:
        return max(0.0, self.next_at - time.monotonic())

    def spend(self, cost: int) -> None:
        if not self.rate:
            return
        self.next_at = max(self.next_at, time.monotonic()) + cost / self.rate


class AiDetectionStage(Stage):
    name = "ai_detection"
    title = "AI Detection"
    description = (
        "Identify model servers, AI gateways, AI applications and MCP servers "
        "on every web asset."
    )
    phase = Phase.DEPTH.value
    depends_on = frozenset({"http_probe"})
    group = StageGroup.ANALYSIS.value
    role = StageRole.CAPABILITY.value
    consumes = frozenset({AssetKind.HTTP_ASSETS.value})
    applies_to = ALL_TARGETS
    tools = ("julius",)
    transport_tool = TransportTool.JULIUS.value
    config_model = AiDetectionConfig

    def run(self) -> StageResult:
        self._check_abort()
        cfg: AiDetectionConfig = self.cfg
        roots, over_cap = self._roots(cfg.max_assets)
        if not roots:
            return StageResult(counts={"probed": 0, "ai_services": 0})

        transport = self.transport
        concurrency = max(1, min(JULIUS_CONCURRENCY, transport.threads))
        if transport.rate:
            concurrency = max(1, min(concurrency, transport.rate))
        net = self.net_options()
        options = {
            "concurrency": concurrency,
            "timeout": transport.timeout,
            "proxy_url": net.proxy_url,
            "headers": net.headers,
        }
        try:
            client = JuliusClient(
                options=JuliusOptions(**options),
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("julius"),
            )
            mcp_client = (
                JuliusClient(
                    options=JuliusOptions(**options, probes_dir=MCP_PROBES_DIR),
                    recorder=self.ctx.recorder,
                    extra_args=self.ctx.resolved.tool_args("julius"),
                )
                if cfg.mcp_paths
                else None
            )
        except JuliusError:
            logger.warning("julius unavailable, skipping AI detection")
            return StageResult(
                counts={"probed": 0, "ai_services": 0},
                warnings=["julius is not installed in the worker image."],
                partial=True,
            )

        batches = self._batches(roots, mcp=mcp_client is not None)
        workers = max(1, transport.threads // concurrency)
        self.emit_progress(
            f"probing {counted(len(roots), 'web asset')} for AI services"
        )
        outcome = self._drive(
            batches,
            client=client,
            mcp_client=mcp_client,
            workers=workers,
            deadline=time.monotonic() + cfg.max_minutes * 60,
        )

        ai_services.fold_onto_hosts(self.session, self.ctx.scan_id)
        self.session.commit()
        self.publish_results(SurfaceDimension.WEB_ASSETS.value)

        warnings: list[str] = []
        if over_cap:
            warnings.append(
                f"{counted(over_cap, 'web asset')} over the web asset budget not probed."
            )
        if outcome.unreached:
            warnings.append(
                f"{counted(outcome.unreached, 'web asset')} not probed within the time budget."
            )
        if outcome.failed:
            warnings.append(
                f"{counted(outcome.failed, 'batch', 'batches')} of julius did not finish."
            )
        self.emit_progress(
            f"{counted(outcome.found, 'AI service')} on "
            f"{counted(outcome.probed, 'web asset')}"
        )
        return StageResult(
            counts={"probed": outcome.probed, "ai_services": outcome.found},
            warnings=warnings,
            partial=bool(warnings),
        )

    def _roots(self, cap: int) -> tuple[list[_Root], int]:
        rows = self.session.execute(
            select(
                HttpAsset.id, HttpAsset.scheme, HttpAsset.host, HttpAsset.port
            ).where(
                HttpAsset.scan_id == self.ctx.scan_id,
                HttpAsset.status_code.isnot(None),
            )
        ).all()
        by_url: dict[str, _Root] = {}
        for asset_id, scheme, host, port in rows:
            if not host or scheme not in ("http", "https"):
                continue
            number = int(port or (443 if scheme == "https" else 80))
            url = f"{scheme}://{host_port(host, number)}"
            root = by_url.setdefault(url, _Root(url=url, host=host, port=number))
            root.assets.append(asset_id)
        ranked = sorted(by_url.values(), key=_rank)
        return ranked[:cap], max(0, len(ranked) - cap)

    def _batches(self, roots: list[_Root], *, mcp: bool) -> deque[_Batch]:
        out: deque[_Batch] = deque()
        for start in range(0, len(roots), BATCH_ASSETS):
            chunk = roots[start : start + BATCH_ASSETS]
            out.append(
                _Batch(
                    targets=[r.url for r in chunk],
                    roots={r.url: r for r in chunk},
                    cost=len(chunk) * REQUESTS_PER_ASSET,
                )
            )
            if not mcp:
                continue
            paths = {f"{r.url}{path}": r for r in chunk for path in MCP_PATHS}
            out.append(
                _Batch(
                    targets=list(paths),
                    roots=paths,
                    cost=len(paths) * _MCP_REQUESTS,
                    mcp=True,
                )
            )
        return out

    def _timeout(self, batch: _Batch) -> int:
        if batch.mcp:
            return len(batch.targets) * self.transport.timeout + 30
        return len(batch.targets) * BATCH_SECONDS_PER_ASSET

    def _drive(
        self,
        batches: deque[_Batch],
        *,
        client: JuliusClient,
        mcp_client: JuliusClient | None,
        workers: int,
        deadline: float,
    ) -> _Outcome:
        outcome = _Outcome()
        pacer = _Pacer(self.transport.rate)
        state = _Ledger(mcp=mcp_client is not None)
        running: dict[Future[JuliusRun], _Batch] = {}

        with ThreadPoolExecutor(max_workers=workers) as pool:
            while batches or running:
                self._check_abort()
                while (
                    batches
                    and len(running) < workers
                    and time.monotonic() < deadline
                    and pacer.wait_seconds() == 0
                ):
                    batch = batches.popleft()
                    pacer.spend(batch.cost)
                    runner = mcp_client if batch.mcp else client
                    future = pool.submit(
                        runner.probe, batch.targets, timeout=self._timeout(batch)
                    )
                    running[future] = batch
                if not running:
                    if not batches or time.monotonic() >= deadline:
                        break
                    time.sleep(min(_POLL_SECONDS, pacer.wait_seconds()))
                    continue
                done, _ = wait(
                    running, timeout=_POLL_SECONDS, return_when=FIRST_COMPLETED
                )
                for future in done:
                    batch = running.pop(future)
                    state.absorb(batch, _result(future), outcome)
                self._write(state.ready(), outcome)

        self._write(state.leftover(), outcome)
        outcome.unreached = sum(len(b.targets) for b in batches if not b.mcp)
        return outcome

    def _write(
        self, settled: list[tuple[_Root, Detection | None]], outcome: _Outcome
    ) -> None:
        if not settled:
            return
        verdicts: dict[UUID, Detection | None] = {}
        for root, verdict in settled:
            verdicts.update(dict.fromkeys(root.assets, verdict))
            outcome.probed += 1
            if verdict is not None:
                outcome.found += 1
        ai_services.record(self.session, verdicts)
        ai_services.fold_onto_hosts(
            self.session, self.ctx.scan_id, {root.host for root, _ in settled}
        )
        self.session.commit()
        self.publish_results(SurfaceDimension.WEB_ASSETS.value)


class _Ledger:
    """Which roots have answered, and which of them can be written."""

    def __init__(self, *, mcp: bool) -> None:
        self.mcp = mcp
        self.found: dict[str, list[Detection]] = {}
        self.probed: dict[str, _Root] = {}
        self.mcp_done: set[str] = set()
        self.written: set[str] = set()

    def absorb(self, batch: _Batch, run: JuliusRun, outcome: _Outcome) -> None:
        broken = run.timed_out or bool(run.error and not run.matches)
        if run.error or run.timed_out:
            outcome.failed += 1
        for target, root in batch.roots.items():
            if batch.mcp:
                self.mcp_done.add(root.url)
            elif not broken:
                self.probed[root.url] = root
            path = target[len(root.url) :]
            for match in run.matches.get(target, []):
                if batch.mcp and match.service != MCP_SERVICE:
                    continue
                self.found.setdefault(root.url, []).append(
                    ai_services.detection(
                        match.service,
                        match.category,
                        match.specificity,
                        (path + match.matched_request) or "/",
                        match.models,
                    )
                )

    def ready(self) -> list[tuple[_Root, Detection | None]]:
        return self._take(lambda url: not self.mcp or url in self.mcp_done)

    def leftover(self) -> list[tuple[_Root, Detection | None]]:
        return self._take(lambda _url: True)

    def _take(self, ok) -> list[tuple[_Root, Detection | None]]:
        out = []
        for url, root in self.probed.items():
            if url in self.written or not ok(url):
                continue
            self.written.add(url)
            out.append((root, ai_services.best(self.found.get(url, []))))
        return out


@dataclass
class _Outcome:
    probed: int = 0
    found: int = 0
    failed: int = 0
    unreached: int = 0


def _result(future: Future[JuliusRun]) -> JuliusRun:
    try:
        return future.result()
    except StageAbortedError:
        raise
    except Exception as exc:
        logger.warning("julius batch failed", error=str(exc))
        return JuliusRun(error=str(exc))


def _rank(root: _Root) -> tuple:
    return (
        root.port not in AI_PORTS,
        root.port in DEFAULT_WEB_PORTS,
        root.host,
        root.port,
    )
