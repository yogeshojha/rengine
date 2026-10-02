from __future__ import annotations

from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError
from tools.runner.models import CommandRecorder

ALTERX_BINARY = "alterx"
DEFAULT_TIMEOUT = 600


class AlterxError(Exception):
    pass


class AlterxClient:
    def __init__(
        self,
        *,
        limit: int,
        recorder: CommandRecorder | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.limit = max(1, limit)
        self.recorder = recorder
        self.extra_args = extra_args or []

        try:
            self._runner = CLIToolRunner(ALTERX_BINARY, default_timeout=DEFAULT_TIMEOUT)
        except ToolNotFoundError as e:
            raise AlterxError(str(e)) from e

    def permute(self, names: list[str]) -> list[str]:
        """Candidate hostnames built from the seeds."""
        if not names:
            return []
        result = self._runner.run(
            args=["-limit", str(self.limit), "-enrich"],
            input_data=names,
            use_stdin=True,
            use_output_file=False,
            output_format=OutputFormat.PLAIN,
            silent=True,
            silent_flag="-silent",
            recorder=self.recorder,
            tool=ALTERX_BINARY,
            extra_args=self.extra_args,
        )
        if not result.success and not result.output_lines:
            raise AlterxError(result.error or "alterx failed")
        seeds = set(names)
        out: list[str] = []
        for line in result.output_lines:
            candidate = line.strip().lower()
            if candidate and candidate not in seeds:
                out.append(candidate)
            if len(out) >= self.limit:
                break
        return out
