from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path

from shared.enums.subdomain import SubdomainSource
from stages.subdomain.providers.base import SubdomainProvider
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError

# our vault provider value -> subfinder source name
_SUBFINDER_KEY_SOURCES = {
    "securitytrails": "securitytrails",
    "chaos": "chaos",
}


class SubfinderProvider(SubdomainProvider):
    tool = "subfinder"
    source = SubdomainSource.SUBFINDER
    binary = "subfinder"

    def _write_provider_config(self) -> Path | None:
        lines: list[str] = []
        for vault_key, source_name in _SUBFINDER_KEY_SOURCES.items():
            key = self.ctx.api_keys.get(vault_key)
            if key:
                lines.append(f"{source_name}:")
                lines.append(f"  - {key}")
        if not lines:
            return None
        fd, path = tempfile.mkstemp(prefix="subfinder_pc_", suffix=".yaml")
        with os.fdopen(fd, "w") as f:
            f.write("\n".join(lines) + "\n")
        return Path(path)

    def discover(self) -> set[str]:
        runner = CLIToolRunner(self.binary, default_timeout=self.ctx.timeout)
        config_path = self._write_provider_config()
        args = ["-d", self.ctx.domain, "-all", "-t", str(self.ctx.threads)]
        if config_path is not None:
            args += ["-provider-config", str(config_path)]
        if self.ctx.proxy_url:
            args += ["-proxy", self.ctx.proxy_url]
        try:
            result = runner.run(
                args=args,
                output_format=OutputFormat.JSONL,
                json_flag="-json",
                silent=True,
                silent_flag="-silent",
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

        hosts = {
            (rec.get("host") or "").strip()
            for rec in result.json_records
            if rec.get("host")
        }
        return {h for h in hosts if h}
