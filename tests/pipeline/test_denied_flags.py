from __future__ import annotations

import pytest

from shared.definitions.tools import denied_flag, parse_tool_args

pytestmark = pytest.mark.pipeline


@pytest.mark.parametrize(
    ("tool", "args", "flag"),
    [
        ("nuclei", "-H /proc/self/environ", "-H"),
        ("nuclei", "-header=/proc/self/environ", "-header"),
        ("katana", "-H /proc/self/environ", "-H"),
        ("katana", "-headers /proc/self/environ", "-headers"),
        ("httpx", "-rr /proc/self/environ", "-rr"),
        ("httpx", "-request /proc/self/environ", "-request"),
        ("httpx", "-path /proc/self/environ", "-path"),
        ("dnsx", "-w /proc/self/environ", "-w"),
        ("dnsx", "-wordlist /proc/self/environ", "-wordlist"),
    ],
)
def test_a_file_or_write_flag_is_denied(tool: str, args: str, flag: str):
    assert denied_flag(tool, parse_tool_args(args)) == flag


@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("nuclei", "-sr"),
        ("nuclei", "-ss host-spray"),
        ("httpx", "-H 'X-Team: red'"),
    ],
)
def test_a_flag_with_the_same_spelling_elsewhere_is_allowed(tool: str, args: str):
    assert denied_flag(tool, parse_tool_args(args)) is None
