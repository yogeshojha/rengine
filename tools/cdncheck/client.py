"""cdncheck CLI client - CDN / WAF / cloud detection via CLIToolRunner."""

from __future__ import annotations

from shared.logging import get_logger
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError
from tools.runner.models import CommandRecorder

logger = get_logger(__name__)

CDNCHECK_BINARY = "cdncheck"
DEFAULT_TIMEOUT = 120


class CdncheckError(Exception):
    """Raised when cdncheck execution fails."""


class CdncheckClient:
    def __init__(
        self,
        *,
        recorder: CommandRecorder | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.recorder = recorder
        self.extra_args = extra_args or []

        try:
            self._runner = CLIToolRunner(
                CDNCHECK_BINARY, default_timeout=DEFAULT_TIMEOUT
            )
        except ToolNotFoundError as e:
            raise CdncheckError(str(e)) from e

    def check(self, ips: list[str]) -> dict[str, dict]:
        """Return {ip: {is_cdn, cdn_name, cdn_type}} for IPs detected as CDN/WAF/cloud."""
        if not ips:
            return {}
        result = self._runner.run(
            args=["-resp"],
            input_data=ips,
            use_stdin=True,
            use_output_file=False,
            output_format=OutputFormat.JSONL,
            json_flag="-jsonl",
            silent=True,
            silent_flag="-silent",
            recorder=self.recorder,
            tool=CDNCHECK_BINARY,
            extra_args=self.extra_args,
        )
        out: dict[str, dict] = {}
        for rec in result.json_records:
            ip = rec.get("input") or rec.get("ip")
            if not ip:
                continue
            if rec.get("cdn"):
                kind, name = "cdn", rec.get("cdn_name")
            elif rec.get("waf"):
                kind, name = "waf", rec.get("waf_name")
            elif rec.get("cloud"):
                kind, name = "cloud", rec.get("cloud_name")
            else:
                continue
            out[str(ip)] = {"is_cdn": True, "cdn_name": name, "cdn_type": kind}
        return out
