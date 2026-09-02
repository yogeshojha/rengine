from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path

from shared.enums.subdomain import SubdomainSource
from stages.subdomain.providers.base import SubdomainProvider, proxy_env
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError


class OneForAllProvider(SubdomainProvider):
    tool = "oneforall"
    source = SubdomainSource.ONEFORALL
    binary = "oneforall"

    def discover(self) -> set[str]:
        runner = CLIToolRunner(self.binary, default_timeout=self.ctx.timeout)
        fd, out_path = tempfile.mkstemp(prefix="oneforall_", suffix=".json")
        os.close(fd)
        try:
            runner.run(
                args=[
                    "--target",
                    self.ctx.domain,
                    "--fmt",
                    "json",
                    "--path",
                    out_path,
                    "run",
                ],
                use_output_file=False,
                output_format=OutputFormat.PLAIN,
                silent=False,
                timeout=self.ctx.timeout,
                env=proxy_env(self.ctx.proxy_url),
                recorder=self.ctx.recorder,
                tool=self.tool,
                extra_args=self.extra_args,
            )
        except ToolNotFoundError:
            return set()

        try:
            payload = Path(out_path).read_text(encoding="utf-8", errors="replace")
            records = json.loads(payload) if payload.strip() else []
        except (OSError, json.JSONDecodeError):
            records = []
        finally:
            with contextlib.suppress(OSError):
                Path(out_path).unlink(missing_ok=True)

        hosts: set[str] = set()
        for rec in records:
            if isinstance(rec, dict):
                value = rec.get("subdomain") or rec.get("domain")
                if value:
                    hosts.add(str(value).strip())
        return hosts
