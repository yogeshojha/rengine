from __future__ import annotations

import pytest

from tools.katana import client as katana
from tools.runner.executor import merge_extra_args

pytestmark = pytest.mark.pipeline

# read off `<tool> -h` in yogeshojha/rengine-worker:3.0.0 on 2026-11-08
MEASURED = {
    "katana": {
        "-H": "-headers",
        "-u": "-list",
        "-o": "-output",
        "-j": "-jsonl",
        "-or": "-omit-raw",
        "-ob": "-omit-body",
        "-nc": "-no-color",
        "-kf": "-known-files",
        "-d": "-depth",
        "-c": "-concurrency",
        "-fs": "-field-scope",
        "-cs": "-crawl-scope",
        "-cos": "-crawl-out-scope",
        "-ct": "-crawl-duration",
        "-rl": "-rate-limit",
        "-jsl": "-jsluice",
        "-jc": "-js-crawl",
        "-aff": "-automatic-form-fill",
        "-iqp": "-ignore-query-params",
        "-ef": "-extension-filter",
        "-hl": "-headless",
        "-scp": "-system-chrome-path",
    },
}

ALIASES = {
    "katana": katana.KATANA_ALIASES,
}


@pytest.mark.parametrize("tool", sorted(MEASURED))
def test_alias_map_matches_the_tool_help(tool):
    assert ALIASES[tool] == MEASURED[tool]


class _Runner:
    def __init__(self, binary, **kwargs):
        self.binary = binary
        self.kwargs = kwargs


def test_katana_runner_carries_the_alias_map(monkeypatch):
    monkeypatch.setattr(katana, "CLIToolRunner", _Runner)
    client = katana.KatanaClient()
    assert client._runner.kwargs["aliases"] is katana.KATANA_ALIASES


def test_katana_short_rate_flag_does_not_restate_the_ceiling():
    args = ["-rate-limit", "5", "-concurrency", "10", "-depth", "3"]
    extra = ["-rl", "9999", "-c", "200", "-d", "9", "-tech-detect"]
    assert merge_extra_args(args, extra, aliases=katana.KATANA_ALIASES) == [
        "-tech-detect"
    ]
