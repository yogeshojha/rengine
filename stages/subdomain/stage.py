from __future__ import annotations

import contextlib
import os
import random
import statistics
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import delete

from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.enums.api_key import APIProvider
from shared.enums.scan import AssetKind, Intensity, Phase, StageGroup, StageRole
from shared.enums.subdomain import SubdomainSource
from shared.logging import get_logger
from shared.models.subdomain import Subdomain
from shared.services.activity_log import ActivityLogService
from shared.services.api_key.sync_api_key import SyncAPIKeyService
from shared.services.scope_filter import matches_any
from shared.services.wordlists import WordlistError, read_words
from shared.utils.datetime import utc_now
from stages.base import DOMAIN_TARGETS, Stage, StageAbortedError, StageResult
from stages.subdomain.config import PASSIVE_TOOLS, SubdomainConfig
from stages.subdomain.parser import merge_and_filter
from stages.subdomain.providers import (
    PASSIVE_PROVIDERS,
    ProviderContext,
    ProviderResult,
    SubdomainProvider,
)
from tools.alterx import AlterxClient, AlterxError
from tools.dnsx.client import DnsxClient, DnsxError

logger = get_logger(__name__)

_PREFETCH_KEYS = (
    APIProvider.SECURITYTRAILS,
    APIProvider.CHAOS,
    APIProvider.NETLAS,
)
_MAX_CONCURRENCY = 8
# above ~50 the resolver silently drops answers rather than going faster (measured)
_MAX_RESOLVE_THREADS = 50
_MIN_RESOLVE_THREADS = 10
# a batch answering far below its peers was throttled, not resolved — retry it
_MIN_BATCHES_FOR_MEDIAN = 3
_DEGRADED_RATIO = 0.5
_SHUFFLE_SEED = 1
# measured: dnsx -t 30 clears ~9 guessed names a second, so 5/s is the floor a
# budget may assume. Guessing is bounded by total time, never by an idle watchdog.
_GUESS_FLOOR_RATE = 5
_GUESS_MIN_BUDGET = 300


# a name close to the apex has more siblings worth guessing than a five-label one
def _seed_rank(name: str) -> tuple[int, int, str]:
    return (name.count("."), len(name), name)


def _guess_budget(count: int) -> int:
    return max(_GUESS_MIN_BUDGET, -(-count // _GUESS_FLOOR_RATE))


def _is_wildcard(info: dict, wildcard_ips: set[str]) -> bool:
    ips = set(info.get("ips") or ())
    return bool(ips) and bool(wildcard_ips) and ips <= wildcard_ips


@dataclass
class _Resolution:
    """What the resolver actually managed, so the stage can report instead of assume."""

    records: dict[str, dict] = field(default_factory=dict)
    submitted: int = 0
    batches: int = 0
    retried: int = 0
    stalled: int = 0
    degraded: int = 0
    unavailable: bool = False

    @property
    def answered(self) -> int:
        return len(self.records)

    @property
    def lost(self) -> bool:
        return self.unavailable or bool(self.stalled or self.degraded)


@dataclass
class _Batch:
    names: list[str]
    answered: int = 0
    stalled: bool = False

    @property
    def rate(self) -> float:
        return self.answered / len(self.names) if self.names else 0.0


class SubdomainStage(Stage):
    name = "subdomain_discovery"
    title = "Subdomain Discovery"
    description = (
        "Enumerate subdomains from passive sources, certificates, wordlists and permutations."
    )
    phase = Phase.EXPANSION.value
    group = StageGroup.HOSTS.value
    role = StageRole.CAPABILITY.value
    produces = frozenset({AssetKind.HOSTS.value, AssetKind.ADDRESSES.value})
    applies_to = DOMAIN_TARGETS
    tools = PASSIVE_TOOLS
    api_keys = tuple(p.value for p in _PREFETCH_KEYS)
    touches_target = False
    config_model = SubdomainConfig

    def should_run(self) -> bool:
        cfg = self.cfg
        return cfg.enabled and bool(
            cfg.enabled_sources
            or cfg.tls_discovery
            or cfg.bruteforce
            or cfg.permutations
        )

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg
        resolved = self.ctx.resolved
        domain = self.ctx.target_value.strip().lower().rstrip(".")
        activity = ActivityLogService(self.session)

        api_keys = self._prefetch_keys()
        pctx = ProviderContext(
            domain=domain,
            timeout=cfg.tool_timeout(resolved.intensity),
            threads=cfg.dns_threads,
            proxy_url=resolved.proxy_url,
            api_keys=api_keys,
            recorder=self.ctx.recorder,
            tool_options=dict(resolved.tool_options or {}),
        )

        provider_classes = self._select_providers(cfg)
        results = self._run_providers(provider_classes, pctx, activity)
        self._check_abort()

        merged = merge_and_filter(results, domain, resolved.included_subdomains)
        # a guessed name that lands on the wildcard address is not a discovery, so the
        # probe that decides that has to run before any name is guessed
        wildcard_ips = self._wildcard_ips(domain, cfg)
        extra = self._expand(
            domain, cfg, sorted(merged, key=_seed_rank), wildcard_ips, activity
        )
        if extra:
            merged = merge_and_filter(
                [*results, *extra], domain, resolved.included_subdomains
            )

        # the target itself is in scope — nothing downstream runs without it
        merged.setdefault(domain, set()).add(SubdomainSource.TARGET.value)
        excluded = {n for n in merged if matches_any(n, resolved.excluded_subdomains)}
        logger.info(
            "subdomain merge for %s: %d unique (%d excluded)",
            domain,
            len(merged),
            len(excluded),
        )

        # excluded subdomains are stored but not resolved or processed further
        to_resolve = [n for n in merged if n not in excluded]
        state = self._resolve(to_resolve, cfg)

        active, ips_seen = self._persist(merged, state.records, wildcard_ips, excluded)
        # the stage runner logs the warning + flips the activity to PARTIAL
        return StageResult(
            counts={
                "subdomains": len(merged),
                "active": active,
                "ips": len(ips_seen),
                "excluded": len(excluded),
                **{r.source.value: len(r.subdomains) for r in extra if r.subdomains},
            },
            warnings=self._resolution_warnings(state),
            partial=state.lost,
        )

    def _expand(
        self,
        domain: str,
        cfg: SubdomainConfig,
        seeds: list[str],
        wildcard_ips: set[str],
        activity: ActivityLogService,
    ) -> list[ProviderResult]:
        """Names no public source listed: guessed from a wordlist, then built from what was found."""
        passive = self.ctx.resolved.intensity == Intensity.PASSIVE.value
        out: list[ProviderResult] = []
        if cfg.bruteforce:
            out.append(self._bruteforce(domain, cfg, wildcard_ips, passive=passive))
        if cfg.permutations:
            out.append(self._permute(cfg, seeds, wildcard_ips, passive=passive))
        for result in out:
            self._check_abort()
            self._log_provider(activity, result)
        return out

    @staticmethod
    def _skipped(source: SubdomainSource, reason: str) -> ProviderResult:
        return ProviderResult(source=source, skipped=True, skip_reason=reason)

    @contextlib.contextmanager
    def _wordlist(self, cfg: SubdomainConfig):
        """The word budget is the first N words, because a list is ranked best first."""
        try:
            words, label = read_words(self.session, cfg.wordlist, cfg.wordlist_limit)
        except WordlistError as exc:
            yield None, str(exc)
            return
        if not words:
            yield None, f"{label} has no usable words"
            return
        fd, name = tempfile.mkstemp(prefix="wordlist_", suffix=".txt")
        try:
            with os.fdopen(fd, "w") as handle:
                handle.write("\n".join(words) + "\n")
            yield (name, len(words), label), None
        finally:
            with contextlib.suppress(OSError):
                Path(name).unlink(missing_ok=True)

    def _bruteforce(
        self,
        domain: str,
        cfg: SubdomainConfig,
        wildcard_ips: set[str],
        *,
        passive: bool,
    ) -> ProviderResult:
        source = SubdomainSource.BRUTEFORCE
        if passive:
            return self._skipped(
                source, "a passive scan does not query the target's nameservers"
            )
        client = self._client(cfg)
        if client is None:
            return self._skipped(source, "dnsx is not installed on this instance")

        with self._wordlist(cfg) as (prepared, problem):
            if prepared is None:
                return self._skipped(source, problem or "no wordlist selected")
            path, tried, label = prepared
            self.emit_progress(f"trying {tried:,} names from {label} against {domain}")
            start = time.monotonic()
            found: set[str] = set()
            wildcards = 0
            with client.stream_brute(
                domain, path, timeout=_guess_budget(tried)
            ) as stream:
                for record in stream.records:
                    parsed = self._record(record)
                    if parsed is None:
                        continue
                    name, info = parsed
                    if _is_wildcard(info, wildcard_ips):
                        wildcards += 1
                        continue
                    found.add(name)
                    self._check_abort()

            cut_short = stream.timed_out

        notes = []
        if wildcards:
            notes.append(
                f"{wildcards:,} of {wildcards + len(found):,} answers were the "
                "wildcard address and were dropped"
            )
        if cut_short:
            notes.append(f"stopped at the {_guess_budget(tried):,}s budget")
        return ProviderResult(
            source=source,
            subdomains=found,
            raw_count=len(found),
            note="; ".join(notes) or None,
            duration_seconds=round(time.monotonic() - start, 2),
        )

    def _permute(
        self,
        cfg: SubdomainConfig,
        seeds: list[str],
        wildcard_ips: set[str],
        *,
        passive: bool,
    ) -> ProviderResult:
        source = SubdomainSource.PERMUTATION
        if passive:
            return self._skipped(
                source, "a passive scan does not query the target's nameservers"
            )
        if not seeds:
            return self._skipped(
                source, "nothing was discovered to build variants from"
            )
        try:
            client = AlterxClient(
                limit=cfg.permutation_limit,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("alterx"),
            )
        except AlterxError:
            return self._skipped(source, "alterx is not installed on this instance")

        start = time.monotonic()
        candidates = client.permute(seeds[: cfg.permutation_seeds])
        if not candidates:
            return ProviderResult(source=source, duration_seconds=0.0)
        self.emit_progress(f"resolving {len(candidates):,} name variants")
        client = self._client(cfg)
        if client is None:
            return self._skipped(source, "dnsx is not installed on this instance")
        found: set[str] = set()
        # same contract as bruteforce: a variant that does not exist says nothing back
        with client.stream_query(
            candidates,
            record_types=["a", "aaaa", "cname"],
            timeout=_guess_budget(len(candidates)),
        ) as stream:
            for record in stream.records:
                parsed = self._record(record)
                if parsed is None:
                    continue
                name, info = parsed
                if info.get("active") and not _is_wildcard(info, wildcard_ips):
                    found.add(name)
                self._check_abort()
        notes = [f"{len(candidates):,} variants resolved"]
        if stream.timed_out:
            notes.append("stopped at the budget")
        return ProviderResult(
            source=source,
            subdomains=found,
            raw_count=len(found),
            note="; ".join(notes),
            duration_seconds=round(time.monotonic() - start, 2),
        )

    def _wildcard_ips(self, domain: str, cfg: SubdomainConfig) -> set[str]:
        probe = f"{uuid.uuid4().hex[:12]}.{domain}"
        info = self._resolve([probe], cfg).records.get(probe)
        return set(info["ips"]) if info and info.get("ips") else set()

    @staticmethod
    def _resolution_warnings(state: _Resolution) -> list[str]:
        if state.unavailable:
            return [
                f"dnsx unavailable — {state.submitted:,} names stored unresolved, "
                "so no host reached the rest of the scan"
            ]
        notes: list[str] = []
        if state.stalled:
            notes.append(
                f"{state.stalled} of {state.batches} resolver batches stalled and were "
                f"abandoned — {state.submitted - state.answered:,} names unresolved"
            )
        if state.degraded:
            notes.append(
                f"{state.degraded} of {state.batches} resolver batches answered far "
                "below the others after a retry; some live hosts are likely missing"
            )
        return notes

    def _check_abort(self) -> None:
        if self.ctx.is_aborted is not None and self.ctx.is_aborted():
            raise StageAbortedError

    def _prefetch_keys(self) -> dict[str, str | None]:
        svc = SyncAPIKeyService(self.session)
        return {p.value: svc.get_key_for_provider(p) for p in _PREFETCH_KEYS}

    def _select_providers(self, cfg: SubdomainConfig) -> list[type[SubdomainProvider]]:
        names = list(dict.fromkeys(cfg.enabled_sources))
        if cfg.tls_discovery and "tlsx" not in names:
            names.append("tlsx")
        selected: list[type[SubdomainProvider]] = []
        for name in names:
            provider = PASSIVE_PROVIDERS.get(name)
            if provider is None:
                logger.warning("unknown subdomain provider '%s', skipping", name)
                continue
            if provider not in selected:
                selected.append(provider)
        return selected

    def _run_providers(
        self,
        provider_classes: list[type[SubdomainProvider]],
        pctx: ProviderContext,
        activity: ActivityLogService,
    ) -> list[ProviderResult]:
        if not provider_classes:
            return []
        results: list[ProviderResult] = []
        workers = min(_MAX_CONCURRENCY, len(provider_classes))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(cls(pctx).run): cls for cls in provider_classes}
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                self._log_provider(activity, result)
        return results

    def _log_provider(
        self, activity: ActivityLogService, result: ProviderResult
    ) -> None:
        source = result.source.value
        if result.skipped:
            message = f"{source} skipped — {result.skip_reason}"
            level = ActivityLevel.WARNING
        elif result.error:
            message = f"{source} failed — {result.error}"
            level = ActivityLevel.WARNING
        else:
            message = f"{source} found {result.raw_count} hosts"
            level = ActivityLevel.INFO
        activity.log(
            event=ActivityEvent.SCAN_PROGRESS,
            title="Subdomain discovery",
            description=message,
            level=level,
            project_id=self.ctx.project_id,
            target_id=self.ctx.target_id,
            scan_id=self.ctx.scan_id,
            target_value=self.ctx.target_value,
        )
        self.session.commit()
        self.emit_progress(message, source=source)

    def _client(self, cfg: SubdomainConfig) -> DnsxClient | None:
        threads = min(max(cfg.dns_threads, _MIN_RESOLVE_THREADS), _MAX_RESOLVE_THREADS)
        try:
            return DnsxClient(
                timeout=max(120, cfg.tool_timeout(self.ctx.resolved.intensity)),
                threads=threads,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("dnsx"),
            )
        except DnsxError:
            logger.warning("dnsx unavailable, storing subdomains without resolution")
            return None

    @staticmethod
    def _record(rec: dict) -> tuple[str, dict] | None:
        host = (rec.get("host") or "").strip().lower().rstrip(".")
        if not host:
            return None
        ips = [str(x) for x in [*(rec.get("a") or []), *(rec.get("aaaa") or [])]]
        cname_list = rec.get("cname") or []
        cname = str(cname_list[0]) if cname_list else None
        return host, {
            "ips": ips,
            "cname": cname,
            "active": bool(ips) or bool(cname),
        }

    def _run_batch(
        self, client: DnsxClient, names: list[str], cfg: SubdomainConfig
    ) -> tuple[dict[str, dict], bool]:
        """Resolve one batch, keeping every record that landed even if the run is killed."""
        out: dict[str, dict] = {}
        with client.stream_query(
            names,
            record_types=["a", "aaaa", "cname"],
            idle_timeout=cfg.dns_idle_timeout,
        ) as stream:
            for rec in stream.records:
                parsed = self._record(rec)
                if parsed is not None:
                    out[parsed[0]] = parsed[1]
                self._check_abort()
        return out, stream.timed_out

    def _resolve(self, names: list[str], cfg: SubdomainConfig) -> _Resolution:
        state = _Resolution(submitted=len(names))
        if not names:
            return state
        client = self._client(cfg)
        if client is None:
            state.unavailable = True
            return state

        # shuffled so every batch is a random sample — otherwise clustered dead
        # names look like a throttled batch and the peer comparison is meaningless
        shuffled = list(names)
        random.Random(_SHUFFLE_SEED).shuffle(shuffled)  # noqa: S311
        size = max(1, cfg.dns_batch_size)
        batches = [
            _Batch(names=shuffled[i : i + size]) for i in range(0, len(shuffled), size)
        ]
        state.batches = len(batches)

        for done, (batch, (records, stalled)) in enumerate(
            self._resolve_batches(client, batches, cfg), start=1
        ):
            state.records.update(records)
            batch.answered = len(records)
            batch.stalled = stalled
            self.emit_progress(
                f"resolved {state.answered:,}/{len(names):,} names "
                f"(batch {done}/{len(batches)})"
            )

        self._retry_degraded(client, batches, state, cfg)
        return state

    def _resolve_batches(
        self, client: DnsxClient, batches: list[_Batch], cfg: SubdomainConfig
    ):
        """Batches are independent, so several resolver invocations run at once."""
        workers = min(max(1, cfg.dns_batch_concurrency), len(batches))
        if workers == 1:
            for batch in batches:
                yield batch, self._run_batch(client, batch.names, cfg)
            return
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(self._run_batch, client, batch.names, cfg): batch
                for batch in batches
            }
            for future in as_completed(futures):
                yield futures[future], future.result()

    def _retry_degraded(
        self,
        client: DnsxClient,
        batches: list[_Batch],
        state: _Resolution,
        cfg: SubdomainConfig,
    ) -> None:
        """A batch far below its peers was throttled, not answered — resolve it again."""
        healthy = [b.rate for b in batches if not b.stalled]
        floor = (
            statistics.median(healthy) * _DEGRADED_RATIO
            if len(healthy) >= _MIN_BATCHES_FOR_MEDIAN
            else 0.0
        )
        suspect = [b for b in batches if b.stalled or b.rate < floor]
        if not suspect:
            return
        self.emit_progress(f"re-resolving {len(suspect)} degraded batch(es)")
        retries = [
            (batch, [n for n in batch.names if n not in state.records])
            for batch in suspect
        ]
        retries = [(batch, pending) for batch, pending in retries if pending]
        state.retried += len(retries)
        for batch, (records, stalled) in self._retry_batches(client, retries, cfg):
            batch.stalled = stalled
            state.records.update(records)
            batch.answered += len(records)
        # count what is still bad after the retry — a recovered batch lost nothing
        state.stalled = sum(1 for b in batches if b.stalled)
        state.degraded = sum(
            1 for b in batches if not b.stalled and floor and b.rate < floor
        )

    def _retry_batches(
        self,
        client: DnsxClient,
        retries: list[tuple[_Batch, list[str]]],
        cfg: SubdomainConfig,
    ):
        workers = min(max(1, cfg.dns_batch_concurrency), len(retries) or 1)
        if workers == 1:
            for batch, pending in retries:
                yield batch, self._run_batch(client, pending, cfg)
            return
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(self._run_batch, client, pending, cfg): batch
                for batch, pending in retries
            }
            for future in as_completed(futures):
                yield futures[future], future.result()

    def _persist(
        self,
        merged: dict[str, set[str]],
        resolution: dict[str, dict],
        wildcard_ips: set[str],
        excluded: set[str],
    ) -> tuple[int, set[str]]:
        self.session.execute(
            delete(Subdomain).where(Subdomain.scan_id == self.ctx.scan_id)
        )
        now = utc_now()
        active = 0
        ips_seen: set[str] = set()
        for name, sources in merged.items():
            is_excluded = name in excluded
            info = {} if is_excluded else resolution.get(name, {})
            ips = info.get("ips", [])
            is_active = bool(info.get("active", False))
            if is_active:
                active += 1
            ips_seen.update(ips)
            is_wildcard = bool(ips) and bool(wildcard_ips) and set(ips) <= wildcard_ips
            self.session.add(
                Subdomain(
                    scan_id=self.ctx.scan_id,
                    target_id=self.ctx.target_id,
                    project_id=self.ctx.project_id,
                    name=name,
                    sources=sorted(sources),
                    resolved_ips=ips,
                    cname=info.get("cname"),
                    is_active=is_active,
                    is_wildcard=is_wildcard,
                    is_excluded=is_excluded,
                    discovered_at=now,
                )
            )
        self.session.commit()
        return active, ips_seen
