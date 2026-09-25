from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path

from sqlalchemy import select

from shared.definitions.intensity import TransportTool
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.enums.subdomain import SubdomainSource
from shared.logging import get_logger
from shared.models.subdomain import Subdomain
from shared.services.scope_filter import matches_any
from shared.services.wordlists import WordlistError, lookup, resolve_path
from shared.utils.datetime import utc_now
from shared.utils.validation import normalize_host
from stages.base import DOMAIN_TARGETS, Stage, StageResult
from stages.vhost.config import BUDGET_SECONDS_PER_IP, VhostConfig
from tools.ffuf.client import FfufClient, FfufError

logger = get_logger(__name__)

_MAX_IPS = 25
_MAX_DISCOVERED_LABELS = 1000
_CATCH_ALL_RATIO = 0.35
_MIN_FOR_RATIO = 20


def host_for(label: str, apex: str) -> str | None:
    """The host name a virtual-host label answers for, in its stored form."""
    return normalize_host(f"{label}.{apex}")


class VhostStage(Stage):
    name = "vhost"
    title = "Virtual Host Discovery"
    description = (
        "Find virtual hosts that DNS does not resolve, by varying the Host header."
    )
    phase = Phase.EXPANSION.value
    depends_on = frozenset({"reverse_dns", "subdomain_discovery"})
    group = StageGroup.HOSTS.value
    role = StageRole.CAPABILITY.value
    consumes = frozenset({AssetKind.HOSTS.value})
    produces = frozenset({AssetKind.HOSTS.value})
    applies_to = DOMAIN_TARGETS
    tools = ("ffuf",)
    transport_tool = TransportTool.FFUF.value
    config_model = VhostConfig

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg
        row = lookup(self.session, cfg.wordlist)
        if row is None:
            logger.warning("vhost wordlist not in the library: %s", cfg.wordlist)
            return StageResult(
                counts={"subdomains": 0},
                warnings=[f"No wordlist named {cfg.wordlist} in the library"],
                partial=True,
            )
        try:
            wordlist = resolve_path(row)
        except WordlistError as exc:
            return StageResult(
                counts={"subdomains": 0}, warnings=[str(exc)], partial=True
            )
        if not wordlist.is_file():
            return StageResult(
                counts={"subdomains": 0},
                warnings=[f"The file for wordlist {row.name} is missing"],
                partial=True,
            )

        apex = self.ctx.target_value.strip().lower().rstrip(".")
        ips = self._candidate_ips()
        if not ips:
            return StageResult(counts={"subdomains": 0})

        candidates, total = self._wordlist_with_discovered(wordlist, apex)
        net = self.net_options()
        try:
            client = FfufClient(
                wordlist=str(candidates),
                threads=self.transport.threads,
                rate=self.transport.rate or 1,
                request_timeout=self.transport.timeout,
                proxy_url=net.proxy_url,
                headers=net.headers,
                probe_scheme=net.probe_scheme,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("ffuf"),
            )
        except FfufError as exc:
            logger.warning("ffuf unavailable, skipping vhost discovery")
            self._discard(candidates, wordlist)
            return StageResult(warnings=[str(exc)], partial=True)

        found: dict[str, set[str]] = {}
        catch_all = 0
        try:
            for ip in ips:
                self._check_abort()
                labels = client.vhost(ip, apex, budget=BUDGET_SECONDS_PER_IP)
                if self._is_catch_all(labels, total):
                    catch_all += 1
                    continue
                for label in labels:
                    if name := host_for(label, apex):
                        found.setdefault(name, set()).add(ip)
        finally:
            self._discard(candidates, wordlist)

        count = self._persist(found)
        self.emit_progress(f"discovered {count} virtual hosts")
        warnings = (
            [
                f"{catch_all} of {len(ips)} addresses answered every host and were dropped"
            ]
            if catch_all
            else []
        )
        return StageResult(counts={"subdomains": count}, warnings=warnings)

    @staticmethod
    def _is_catch_all(labels: list[str], total: int) -> bool:
        return total >= _MIN_FOR_RATIO and len(labels) > total * _CATCH_ALL_RATIO

    @staticmethod
    def _discard(candidates: Path, base: Path) -> None:
        if candidates != base:
            with contextlib.suppress(OSError):
                candidates.unlink(missing_ok=True)

    def _wordlist_with_discovered(self, base: Path, apex: str) -> tuple[Path, int]:
        """The base wordlist plus the labels of names already found, as one file."""
        words: dict[str, None] = {}
        with contextlib.suppress(OSError):
            for line in base.read_text(encoding="utf-8", errors="replace").splitlines():
                word = line.strip()
                if word and not word.startswith("#"):
                    words.setdefault(word, None)
        base_count = len(words)
        for label in self._discovered_labels(apex):
            words.setdefault(label, None)
        if len(words) == base_count:
            return base, base_count
        fd, path = tempfile.mkstemp(suffix=".txt", prefix="vhost_")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(words))
        return Path(path), len(words)

    def _discovered_labels(self, apex: str) -> list[str]:
        suffix = f".{apex}"
        names = (
            self.session.execute(
                select(Subdomain.name).where(Subdomain.scan_id == self.ctx.scan_id)
            )
            .scalars()
            .all()
        )
        labels: dict[str, None] = {}
        for name in names:
            if name and name.endswith(suffix):
                label = name[: -len(suffix)]
                if label and "*" not in label:
                    labels.setdefault(label, None)
            if len(labels) >= _MAX_DISCOVERED_LABELS:
                break
        return list(labels)

    def _candidate_ips(self) -> list[str]:
        subs = (
            self.session.execute(
                select(Subdomain).where(
                    Subdomain.scan_id == self.ctx.scan_id,
                    Subdomain.is_active.is_(True),
                )
            )
            .scalars()
            .all()
        )
        resolvable: list[str] = []
        wildcard: list[str] = []
        seen: set[str] = set()
        for sub in subs:
            bucket = wildcard if sub.is_wildcard else resolvable
            for ip in sub.resolved_ips or []:
                if ip not in seen:
                    seen.add(ip)
                    bucket.append(ip)
        return (resolvable + wildcard)[:_MAX_IPS]

    def _persist(self, found: dict[str, set[str]]) -> int:
        existing = set(
            self.session.execute(
                select(Subdomain.name).where(Subdomain.scan_id == self.ctx.scan_id)
            )
            .scalars()
            .all()
        )
        now = utc_now()
        added = 0
        excluded = self.ctx.resolved.excluded_subdomains or []
        for name, ips in found.items():
            if name in existing:
                continue
            self.session.add(
                Subdomain(
                    scan_id=self.ctx.scan_id,
                    target_id=self.ctx.target_id,
                    project_id=self.ctx.project_id,
                    name=name,
                    sources=[SubdomainSource.VHOST.value],
                    resolved_ips=sorted(ips),
                    cname=None,
                    is_active=True,
                    is_wildcard=False,
                    is_excluded=matches_any(name, excluded),
                    discovered_at=now,
                )
            )
            added += 1
        self.session.commit()
        return added
