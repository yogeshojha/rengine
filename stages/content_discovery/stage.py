from __future__ import annotations

import contextlib
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select

from shared.definitions.endpoints import EndpointSource
from shared.definitions.surface import SurfaceDimension
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.logging import get_logger
from shared.models.http_asset import HttpAsset
from shared.services import endpoint_inventory
from shared.services.endpoint_inventory import EndpointObservation
from shared.services.wordlists import WordlistError, read_words
from stages.base import ALL_TARGETS, Stage, StageResult
from stages.content_discovery.config import ContentDiscoveryConfig
from tools.ffuf.client import FfufClient, FfufError
from tools.ffuf.parser import parse_ffuf_record

logger = get_logger(__name__)

_HTTP_SERVER_ERROR = 500
_SINK_ROWS = 200
_MAX_WORKERS = 4
_DRAIN_SECONDS = 5
_MIN_HOST_BUDGET = 30
MAX_HIT_SHARE = 0.25
_NAMED = 3


class ContentDiscoveryStage(Stage):
    """Paths guessed from a ranked wordlist against every live site."""

    name = "content_discovery"
    title = "Content Discovery"
    description = "Guess common paths and files against every live site and keep the ones that answer."
    phase = Phase.DEPTH.value
    depends_on = frozenset({"http_probe"})
    group = StageGroup.ENDPOINTS.value
    role = StageRole.CAPABILITY.value
    consumes = frozenset({AssetKind.HTTP_ASSETS.value})
    produces = frozenset({AssetKind.ENDPOINTS.value})
    applies_to = ALL_TARGETS
    tools = ("ffuf",)
    touches_target = True
    config_model = ContentDiscoveryConfig
    launch_fields = (
        "enabled",
        "wordlist",
        "wordlist_limit",
        "max_hosts",
        "max_minutes",
    )

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg
        hosts = self._hosts(cfg.max_hosts)
        if not hosts:
            self.emit_progress("no live site to guess against")
            return StageResult(counts={"endpoints": 0, "hosts": 0})

        with self._files(cfg) as (prepared, problem):
            if prepared is None:
                return StageResult(
                    counts={"endpoints": 0, "hosts": 0},
                    warnings=[problem or "no wordlist selected"],
                    partial=True,
                )
            word_file, tried, label = prepared
            self.emit_progress(
                f"guessing {tried:,} paths from {label} against {len(hosts)} site"
                f"{'' if len(hosts) == 1 else 's'}"
            )
            return self._fuzz(cfg, hosts, word_file, tried, label)

    def _fuzz(self, cfg, hosts, word_file, tried, label) -> StageResult:
        args = {
            "wordlist": word_file,
            "threads": cfg.threads,
            "rate": cfg.rate,
            "request_timeout": cfg.timeout,
            "proxy_url": self.net_options().proxy_url,
            "headers": self.net_options().headers,
            "recorder": self.ctx.recorder,
            "extra_args": self.ctx.resolved.tool_args("ffuf"),
        }
        try:
            FfufClient(**args)
        except FfufError as e:
            return StageResult(
                counts={"endpoints": 0, "hosts": len(hosts)},
                warnings=[str(e)],
                partial=True,
            )

        rounds = max(1, -(-len(hosts) // _MAX_WORKERS))
        per_host = max(_MIN_HOST_BUDGET, (cfg.max_minutes * 60) // rounds)
        sink = self.results_sink(
            SurfaceDimension.ENDPOINTS.value, self._write, rows=_SINK_ROWS
        )
        state = _Run()
        workers = min(_MAX_WORKERS, len(hosts))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(self._one, args, host, word_file, per_host, tried)
                for host in hosts
            }
            remaining = futures
            while remaining:
                done, remaining = wait(remaining, timeout=_DRAIN_SECONDS)
                for future in done:
                    outcome = future.result()
                    state.absorb(outcome)
                    for parsed in outcome.kept:
                        sink.add(_observation(parsed, label))
                self._check_abort()
        written = sink.close()

        self.emit_progress(state.note(written, tried, len(hosts)))
        return StageResult(
            counts={
                "endpoints": written,
                "hosts": len(hosts),
                "uncalibrated": state.uncalibrated,
            },
            warnings=state.warnings(cfg, tried),
            partial=bool(state.cut_short or state.failed),
        )

    def _one(self, args: dict, host: str, word_file: str, budget: int, tried: int):
        """One site, in its own ffuf process."""
        outcome = _Outcome(host=host)
        try:
            client = FfufClient(**args)
            with client.stream_content(host, word_file, budget=budget) as stream:
                for record in stream.records:
                    parsed = parse_ffuf_record(record)
                    if parsed is not None:
                        outcome.hits.append(parsed)
                    if self.aborted():
                        break
            outcome.cut_short = bool(stream.timed_out)
        except (FfufError, OSError) as e:
            outcome.error = str(e)[:200]
            return outcome
        outcome.settle(tried)
        return outcome

    def aborted(self) -> bool:
        return bool(self.ctx.is_aborted and self.ctx.is_aborted())

    def _write(self, batch: list[EndpointObservation]) -> int:
        result = endpoint_inventory.upsert(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            source=EndpointSource.FUZZ.value,
            observations=batch,
        )
        self.session.commit()
        return result.created + result.updated

    def _hosts(self, limit: int) -> list[str]:
        """Sites that answered, best status first."""
        rows = self.session.execute(
            select(HttpAsset.url, HttpAsset.status_code)
            .where(
                HttpAsset.scan_id == self.ctx.scan_id,
                HttpAsset.status_code.isnot(None),
            )
            .order_by(HttpAsset.status_code.asc(), HttpAsset.url.asc())
        ).all()
        picked: list[str] = []
        seen: set[str] = set()
        for url, status in rows:
            if not url or status is None or status >= _HTTP_SERVER_ERROR:
                continue
            base = url.rstrip("/")
            if base in seen:
                continue
            seen.add(base)
            picked.append(base)
            if len(picked) >= limit:
                break
        return picked

    @contextlib.contextmanager
    def _files(self, cfg):
        try:
            words, label = read_words(self.session, cfg.wordlist, cfg.wordlist_limit)
        except WordlistError as exc:
            yield None, str(exc)
            return
        if not words:
            yield None, f"{label} has no usable words"
            return
        word_path = _spill(words, prefix="ffuf_words_")
        try:
            yield (word_path, len(words), label), None
        finally:
            with contextlib.suppress(OSError):
                Path(word_path).unlink(missing_ok=True)


@dataclass
class _Outcome:
    host: str
    hits: list[dict] = field(default_factory=list)
    kept: list[dict] = field(default_factory=list)
    uncalibrated: bool = False
    cut_short: bool = False
    error: str | None = None

    def settle(self, tried: int) -> None:
        share = len(self.hits) / tried if tried else 0
        self.uncalibrated = share >= MAX_HIT_SHARE
        self.kept = [] if self.uncalibrated else self.hits


@dataclass
class _Run:
    kept: int = 0
    uncalibrated: int = 0
    cut_short: int = 0
    failed: int = 0
    dropped: list[str] = field(default_factory=list)

    def absorb(self, outcome: _Outcome) -> None:
        if outcome.error:
            self.failed += 1
            return
        if outcome.cut_short:
            self.cut_short += 1
        if outcome.uncalibrated:
            self.uncalibrated += 1
            self.dropped.append(outcome.host)
            return
        self.kept += len(outcome.kept)

    def note(self, written: int, tried: int, hosts: int) -> str:
        text = f"{written:,} paths answered out of {tried:,} guessed on {hosts} sites"
        if self.uncalibrated:
            text += (
                f"; {self.uncalibrated} site(s) answered to everything and were dropped"
            )
        return text

    def warnings(self, cfg, tried: int) -> list[str]:
        out: list[str] = []
        if self.uncalibrated:
            shown = ", ".join(self.dropped[:_NAMED])
            extra = len(self.dropped) - _NAMED
            more = f" and {extra} more" if extra > 0 else ""
            out.append(
                f"{self.uncalibrated} site(s) answered to at least "
                f"{int(MAX_HIT_SHARE * 100)}% of {tried:,} guessed paths, which is a "
                f"catch-all response rather than content: {shown}{more}. Nothing from "
                "them was stored."
            )
        if self.cut_short:
            out.append(
                f"{self.cut_short} site(s) hit the {cfg.max_minutes}-minute budget "
                "before the whole wordlist was tried."
            )
        if self.failed:
            out.append(f"{self.failed} site(s) could not be guessed against.")
        return out


def _spill(lines: list[str], *, prefix: str) -> str:
    fd, name = tempfile.mkstemp(prefix=prefix, suffix=".txt")
    with os.fdopen(fd, "w") as handle:
        handle.write("\n".join(lines) + "\n")
    return name


def _observation(parsed: dict, label: str) -> EndpointObservation:
    return EndpointObservation(
        url=parsed["url"],
        found_on=None,
        detail=f"Guessed from {label} and answered {parsed['status_code']}",
        is_probed=True,
        status_code=parsed["status_code"],
        content_length=parsed["content_length"],
        content_type=parsed["content_type"],
        words=parsed["words"],
        lines=parsed["lines"],
        redirect_location=parsed["redirect_location"],
    )
