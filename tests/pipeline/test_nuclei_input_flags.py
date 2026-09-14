from __future__ import annotations

from types import SimpleNamespace

import pytest

from tools.nuclei.client import NucleiClient, NucleiOptions

pytestmark = pytest.mark.pipeline


def _args(**over) -> list[str]:
    return NucleiClient.args(
        SimpleNamespace(options=NucleiOptions(templates_file="templates.txt", **over))
    )


def _value(args: list[str], flag: str) -> str | None:
    return args[args.index(flag) + 1] if flag in args else None


def test_host_spray_is_the_default_strategy() -> None:
    assert _value(_args(), "-scan-strategy") == "host-spray"


def test_protocol_types_are_passed_as_one_list() -> None:
    args = _args(protocol_types=("tcp", "ssl", "javascript"))
    assert _value(args, "-type") == "tcp,ssl,javascript"
    assert "-type" not in _args()


def test_dast_is_a_switch_with_its_parameter_patience() -> None:
    args = _args(dast=True, fuzz_param_frequency=7)
    assert "-dast" in args
    assert _value(args, "-fuzz-param-frequency") == "7"
    plain = _args()
    assert "-dast" not in plain
    assert "-fuzz-param-frequency" not in plain


def test_no_time_cap_when_minutes_is_zero() -> None:
    assert "-max-time" not in _args(max_minutes=0)
    assert _value(_args(max_minutes=15), "-max-time") == "15m"


def test_silent_is_never_passed() -> None:
    assert "-silent" not in _args()
