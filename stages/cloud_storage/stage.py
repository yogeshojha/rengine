from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
from sqlalchemy import select

from shared.definitions.cloud_storage import (
    CLOUD_STORAGE_STAGE,
    MAX_CANDIDATES,
    OPEN_ACCESS,
    PROBE_TIMEOUT,
    SLOW_DOWN_BACKOFF,
)
from shared.definitions.domains import registrable_domain
from shared.definitions.intensity import TransportTool
from shared.enums.scan import AssetKind, Intensity, Phase, StageGroup, StageRole
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.endpoint import Endpoint
from shared.models.http_asset import HttpAsset
from shared.models.subdomain import Subdomain
from shared.services import cloud_storage
from shared.services.cloud_storage import Bucket, Candidate, ThrottledError
from shared.utils.text import counted
from shared.utils.validation import normalize_domain
from stages.base import Stage, StageResult
from stages.cloud_storage.config import (
    PROBE_RATE_CAP,
    PROBE_THREAD_CAP,
    CloudStorageConfig,
)

logger = get_logger(__name__)

_READ_CAP = 20_000


class _Gate:
    """One request at a time per the rate, backing off when a cloud says slow down."""

    def __init__(self, rate: int) -> None:
        self._lock = threading.Lock()
        self._interval = 1.0 / max(rate, 1)
        self._next = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            start = max(now, self._next)
            self._next = start + self._interval
        if start > now:
            time.sleep(start - now)

    def back_off(self) -> None:
        with self._lock:
            self._interval = min(self._interval * SLOW_DOWN_BACKOFF, 2.0)


class CloudStorageStage(Stage):
    name = CLOUD_STORAGE_STAGE
    title = "Cloud storage"
    description = (
        "Find storage buckets named after the target and report which are open."
    )
    phase = Phase.DISCOVERY.value
    depends_on = frozenset({"subdomain_discovery", "seed_resolution", "http_probe"})
    group = StageGroup.ANALYSIS.value
    role = StageRole.CAPABILITY.value
    consumes = frozenset(
        {AssetKind.HOSTS.value, AssetKind.HTTP_ASSETS.value, AssetKind.ENDPOINTS.value}
    )
    applies_to = frozenset({TargetType.DOMAIN.value, TargetType.URL.value})
    tools = ()
    transport_tool = TransportTool.HTTPX.value
    touches_target = True
    passive_capable = True
    config_model = CloudStorageConfig

    def run(self) -> StageResult:
        self._check_abort()
        cfg: CloudStorageConfig = self.cfg
        host = normalize_domain(self.ctx.target_value)
        apex = registrable_domain(host) or host
        if not apex or "." not in apex:
            return StageResult(counts={"candidates": 0, "cloud_buckets": 0})
        label = apex.partition(".")[0]

        referenced = self._referenced()
        passive = self.ctx.resolved.intensity == Intensity.PASSIVE.value
        guess = cfg.guess and not passive
        found = cloud_storage.candidates(
            label=label,
            hostnames=[] if passive else self._hostnames(),
            referenced=referenced,
            words=cfg.words,
            guess=guess,
            cap=MAX_CANDIDATES,
        )
        if not found.items:
            return StageResult(counts={"candidates": 0, "cloud_buckets": 0})

        self.emit_progress(
            f"checking {counted(len(found.items), 'bucket name')} across cloud providers"
        )
        buckets, partial = self._probe(found.items)

        stored = cloud_storage.replace_rows(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            buckets=buckets,
        )
        self.session.commit()
        opened = sum(1 for b in buckets if b.probe.access in OPEN_ACCESS)
        self.emit_progress(
            f"{counted(stored, 'bucket')}, {opened} open"
            if stored
            else "no buckets found"
        )
        warnings = []
        if found.capped:
            warnings.append(f"Candidate names capped at {MAX_CANDIDATES:,}.")
        return StageResult(
            counts={
                "candidates": len(found.items),
                "cloud_buckets": stored,
                "cloud_buckets_open": opened,
            },
            warnings=warnings,
            partial=partial or found.capped,
        )

    def _hostnames(self) -> list[str]:
        rows = self.session.execute(
            select(Subdomain.name)
            .where(
                Subdomain.scan_id == self.ctx.scan_id,
                Subdomain.is_excluded.is_(False),
            )
            .limit(_READ_CAP)
        ).scalars()
        return [str(r) for r in rows if r]

    def _referenced(self) -> list[Candidate]:
        hosts = list(
            self.session.execute(
                select(HttpAsset.host)
                .where(HttpAsset.scan_id == self.ctx.scan_id)
                .limit(_READ_CAP)
            ).scalars()
        )
        cnames = list(
            self.session.execute(
                select(Subdomain.cname).where(
                    Subdomain.scan_id == self.ctx.scan_id,
                    Subdomain.cname.isnot(None),
                )
            ).scalars()
        ) + list(
            self.session.execute(
                select(HttpAsset.cname).where(
                    HttpAsset.scan_id == self.ctx.scan_id,
                    HttpAsset.cname.isnot(None),
                )
            ).scalars()
        )
        urls = list(
            self.session.execute(
                select(HttpAsset.url, HttpAsset.final_url).where(
                    HttpAsset.scan_id == self.ctx.scan_id
                )
            )
        )
        flat_urls = [u for pair in urls for u in pair if u]
        flat_urls += list(
            self.session.execute(
                select(Endpoint.url)
                .where(Endpoint.scan_id == self.ctx.scan_id)
                .limit(_READ_CAP)
            ).scalars()
        )
        return cloud_storage.referenced_in(
            hosts=[str(h) for h in hosts if h],
            cnames=[str(c) for c in cnames if c],
            urls=[str(u) for u in flat_urls if u],
        )

    def _probe(self, items: list[Candidate]) -> tuple[list[Bucket], bool]:
        rate = min(self.transport.rate or PROBE_RATE_CAP, PROBE_RATE_CAP)
        workers = min(max(self.transport.threads, 1), PROBE_THREAD_CAP)
        gate = _Gate(rate)
        client = cloud_storage.client(self.net_options().proxy_url, PROBE_TIMEOUT)
        buckets: list[Bucket] = []
        partial = False
        lock = threading.Lock()

        def one(candidate: Candidate) -> list[Bucket]:
            gate.wait()
            try:
                return cloud_storage.probe(client, candidate)
            except ThrottledError:
                gate.back_off()
                return []
            except httpx.HTTPError:
                return []

        with client, ThreadPoolExecutor(max_workers=workers) as pool:
            step = workers * 4
            for start in range(0, len(items), step):
                self._check_abort()
                for result in pool.map(one, items[start : start + step]):
                    with lock:
                        buckets.extend(result)
        return buckets, partial
