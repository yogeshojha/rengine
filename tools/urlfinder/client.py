from __future__ import annotations

from shared.logging import get_logger
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError
from tools.runner.models import CommandRecorder

logger = get_logger(__name__)

URLFINDER_BINARY = "urlfinder"
DEFAULT_TIMEOUT = 900


class UrlfinderError(Exception):
    pass


class UrlfinderClient:
    """Passive URL discovery from public archives. Keyless, and better with provider keys."""

    def __init__(
        self,
        *,
        timeout: int = 30,
        threads: int = 10,
        proxy_url: str | None = None,
        recorder: CommandRecorder | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.timeout = timeout
        self.threads = threads
        self.proxy_url = proxy_url
        self.recorder = recorder
        self.extra_args = extra_args or []

        try:
            self._runner = CLIToolRunner(
                URLFINDER_BINARY, default_timeout=DEFAULT_TIMEOUT
            )
        except ToolNotFoundError as e:
            raise UrlfinderError(str(e)) from e

    def collect(self, domain: str) -> list[str]:
        args = [
            "-d",
            domain,
            "-all",
            "-no-color",
            "-timeout",
            str(self.timeout),
            "-t",
            str(self.threads),
        ]
        if self.proxy_url:
            args += ["-proxy", self.proxy_url]
        result = self._runner.run(
            args=args,
            use_output_file=False,
            output_format=OutputFormat.PLAIN,
            silent=True,
            silent_flag="-silent",
            recorder=self.recorder,
            tool=URLFINDER_BINARY,
            extra_args=self.extra_args,
        )
        return [line.strip() for line in result.output_lines if line.strip()]
