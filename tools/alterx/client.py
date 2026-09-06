"""alterx CLI client — permutation candidates generated from names already discovered."""

from __future__ import annotations

from shared.logging import get_logger
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError
from tools.runner.models import CommandRecorder

logger = get_logger(__name__)

ALTERX_BINARY = "alterx"
DEFAULT_TIMEOUT = 600


class AlterxError(Exception):
    pass


class AlterxClient:
    def __init__(
        self,
        *,
        limit: int,
        enrich: bool = True,
        patterns: list[str] | None = None,
        recorder: CommandRecorder | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.limit = max(1, limit)
        self.enrich = enrich
        self.patterns = patterns or []
        self.recorder = recorder
        self.extra_args = extra_args or []

        try:
            self._runner = CLIToolRunner(ALTERX_BINARY, default_timeout=DEFAULT_TIMEOUT)
        except ToolNotFoundError as e:
            raise AlterxError(str(e)) from e

    def permute(self, names: list[str]) -> list[str]:
        """Candidate hostnames built from the seeds. Generates, never resolves."""
        if not names:
            return []
        args = ["-limit", str(self.limit)]
        if self.enrich:
            # words mined from the seeds themselves, which is what beats a blind list
            args.append("-enrich")
        for pattern in self.patterns:
            args += ["-p", pattern]

        result = self._runner.run(
            args=args,
            input_data=names,
            # alterx reads its seeds from stdin; -l with a file path yields "no input found"
            use_stdin=True,
            use_output_file=False,
            output_format=OutputFormat.PLAIN,
            silent=True,
            silent_flag="-silent",
            recorder=self.recorder,
            tool=ALTERX_BINARY,
            extra_args=self.extra_args,
        )
        seeds = set(names)
        out: list[str] = []
        for line in result.output_lines:
            candidate = line.strip().lower()
            if candidate and candidate not in seeds:
                out.append(candidate)
            if len(out) >= self.limit:
                break
        return out
