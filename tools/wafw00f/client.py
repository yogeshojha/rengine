"""wafw00f CLI client - WAF fingerprinting via CLIToolRunner."""

from __future__ import annotations

import json
import re

from shared.logging import get_logger
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError
from tools.runner.models import CommandRecorder

logger = get_logger(__name__)

WAFW00F_BINARY = "wafw00f"
DEFAULT_TIMEOUT = 600


class Wafw00fError(Exception):
    """Raised when wafw00f execution fails."""


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _extract_json_array(raw: str) -> list:
    match = re.search(r"\[\s*\{.*\}\s*\]", _ANSI_RE.sub("", raw), re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


class Wafw00fClient:
    def __init__(
        self,
        *,
        proxy_url: str | None = None,
        recorder: CommandRecorder | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.proxy_url = proxy_url
        self.recorder = recorder
        self.extra_args = extra_args or []

        try:
            self._runner = CLIToolRunner(
                WAFW00F_BINARY, default_timeout=DEFAULT_TIMEOUT
            )
        except ToolNotFoundError as e:
            raise Wafw00fError(str(e)) from e

    def detect(self, urls: list[str]) -> dict[str, str]:
        """Return {url: firewall_name} for URLs fronted by a detected WAF."""
        if not urls:
            return {}
        args = ["-f", "json", "-a", "-o", "/dev/stdout"]
        if self.proxy_url:
            args += ["-p", self.proxy_url]

        result = self._runner.run(
            args=args,
            input_data=urls,
            input_flag="-i",
            use_output_file=False,
            output_format=OutputFormat.PLAIN,
            silent=False,
            recorder=self.recorder,
            tool=WAFW00F_BINARY,
            extra_args=self.extra_args,
        )

        out: dict[str, str] = {}
        for rec in _extract_json_array(result.stdout):
            url = rec.get("url")
            if url and rec.get("detected") and rec.get("firewall"):
                name = rec["firewall"]
                if name and name.lower() not in ("none", "generic"):
                    out[url] = name[:100]
        return out
