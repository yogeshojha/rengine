"""cdncheck CLI client - CDN / WAF / cloud detection via CLIToolRunner."""

from __future__ import annotations

from shared.logging import get_logger
from tools.cdncheck.parser import parse_attributions
from tools.runner import CLIToolRunner, OutputFormat, ToolFlags, ToolNotFoundError
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
                CDNCHECK_BINARY,
                default_timeout=DEFAULT_TIMEOUT,
                recorder=recorder,
                extra_args=self.extra_args,
                flags=ToolFlags(json="-jsonl"),
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
        )
        return parse_attributions(result.json_records)
