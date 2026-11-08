from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
from pathlib import Path

from shared.definitions.api_keys import SUBFINDER_SOURCES, subfinder_value
from shared.enums.subdomain import SubdomainSource
from shared.http import egress_proxy
from stages.subdomain.providers.base import SourceStat, SubdomainProvider
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError

# seconds left between subfinder's own deadline and the process timeout
MAX_TIME_MARGIN = 60
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_STAT_ROW = re.compile(r"^\s*([a-z0-9_]+)\s+\S+\s+(\d+)\s+(\d+)\s+(\d+)\s*$")
_SKIPPED_HEAD = "were included but skipped"
_SOURCE_NAME = re.compile(r"^\s*([a-z0-9_]+)\s*$")


def max_time_minutes(timeout: int) -> int:
    """The `-max-time` that lets subfinder write its results before the process timeout."""
    return max(1, (timeout - MAX_TIME_MARGIN) // 60)


def parse_stats(stderr: str) -> dict[str, SourceStat]:
    """The per-source table `-stats` prints, including the skipped list."""
    stats: dict[str, SourceStat] = {}
    skipped = False
    for raw in _ANSI.sub("", stderr or "").splitlines():
        if _SKIPPED_HEAD in raw:
            skipped = True
            continue
        if skipped:
            found = _SOURCE_NAME.match(raw)
            if found:
                stats[found.group(1)] = SourceStat(skipped=True)
            continue
        row = _STAT_ROW.match(raw)
        if row:
            stats[row.group(1)] = SourceStat(
                results=int(row.group(2)),
                requests=int(row.group(3)),
                errors=int(row.group(4)),
            )
    return stats


def record_sources(rec: dict) -> list[str]:
    sources = rec.get("sources")
    if isinstance(sources, list):
        return [str(s) for s in sources if s]
    source = rec.get("source")
    return [str(source)] if source else []


class SubfinderProvider(SubdomainProvider):
    tool = "subfinder"
    source = SubdomainSource.SUBFINDER
    binary = "subfinder"

    def provider_config(self) -> dict[str, list[str]]:
        """Each keyed source with a stored key, as subfinder reads it."""
        config: dict[str, list[str]] = {}
        for provider, spec in SUBFINDER_SOURCES.items():
            key = self.ctx.api_keys.get(provider.value)
            if not key:
                continue
            value = subfinder_value(
                provider, key, self.ctx.key_meta.get(provider.value)
            )
            if value:
                config[spec.name] = [value]
                self._keyed[spec.name] = provider.value
        return config

    def _write_provider_config(self) -> Path | None:
        config = self.provider_config()
        if not config:
            return None
        fd, path = tempfile.mkstemp(prefix="subfinder_pc_", suffix=".yaml")
        with os.fdopen(fd, "w") as f:
            json.dump(config, f)
        return Path(path)

    def discover(self) -> set[str]:
        runner = CLIToolRunner(self.binary, default_timeout=self.ctx.timeout)
        config_path = self._write_provider_config()
        minutes = max_time_minutes(self.ctx.timeout)
        args = [
            "-d",
            self.ctx.domain,
            "-all",
            "-cs",
            "-stats",
            "-max-time",
            str(minutes),
            "-t",
            str(self.ctx.threads),
        ]
        if config_path is not None:
            args += ["-provider-config", str(config_path)]
        if proxy := egress_proxy():
            args += ["-proxy", proxy]
        try:
            result = runner.run(
                args=args,
                output_format=OutputFormat.JSONL,
                json_flag="-json",
                silent=False,
                timeout=self.ctx.timeout,
                recorder=self.ctx.recorder,
                tool=self.tool,
                extra_args=self.extra_args,
            )
        except ToolNotFoundError:
            return set()
        finally:
            if config_path is not None:
                with contextlib.suppress(OSError):
                    config_path.unlink(missing_ok=True)

        self._checked(result)
        self._stats = parse_stats(result.stderr)
        if result.timed_out or result.duration_seconds >= minutes * 60:
            self._cut = True
            self._note = self._note or f"stopped at its {minutes}-minute budget"
        hosts: set[str] = set()
        for rec in result.json_records:
            host = (rec.get("host") or "").strip()
            if not host:
                continue
            hosts.add(host)
            for name in record_sources(rec):
                self._breakdown.setdefault(name, set()).add(host)
        return hosts
