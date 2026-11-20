from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from tools.cdncheck import client as cdncheck
from tools.dnsx import client as dnsx
from tools.ffuf import client as ffuf
from tools.naabu import client as naabu
from tools.nuclei.client import NUCLEI_ALIASES
from tools.runner.executor import CLIToolRunner, merge_extra_args
from tools.urlfinder import client as urlfinder

pytestmark = pytest.mark.pipeline


def test_a_restated_flag_and_its_value_are_dropped():
    stage = ["-rate-limit", "5", "-threads", "20"]
    extra = ["-rate-limit", "9999", "-retries", "3"]
    assert merge_extra_args(stage, extra) == ["-retries", "3"]


def test_the_equals_spelling_is_dropped_too():
    assert merge_extra_args(["-timeout", "10"], ["-timeout=99", "-silent"]) == [
        "-silent"
    ]


def test_reserved_flags_are_dropped_before_the_runner_adds_them():
    extra = ["-l", "/etc/passwd", "-json", "-o", "elsewhere.txt", "-stats"]
    assert merge_extra_args([], extra, ("-l", "-json", "-o")) == ["-stats"]


def test_a_boolean_flag_does_not_swallow_the_next_flag():
    assert merge_extra_args(["-silent"], ["-silent", "-stats"]) == ["-stats"]


def test_unrelated_flags_pass_through_in_order():
    extra = ["-stats", "-si", "5", "-tags", "cve"]
    assert merge_extra_args(["-rate-limit", "5"], extra) == extra


def test_a_short_spelling_cannot_restate_a_long_flag():
    stage = ["-rate-limit", "150", "-list", "/run/gen.txt", "-max-host-error", "30"]
    extra = ["-rl", "9999", "-l", "/run/mine.txt", "-mhe", "0", "-j", "-stats"]
    assert merge_extra_args(stage, extra, ("-list", "-jsonl"), NUCLEI_ALIASES) == [
        "-stats"
    ]


def test_the_reserved_set_covers_the_short_spelling_too():
    assert merge_extra_args(
        [], ["-l", "x", "-o", "y", "-tags", "cve"], ("-list", "-output"), NUCLEI_ALIASES
    ) == ["-tags", "cve"]


def test_ffuf_drops_a_custom_silent_with_its_own_short_flag():
    extra = ["-silent", "-s", "-ac"]
    assert merge_extra_args([], extra, ("-l", "-json", "-s"), ffuf.FFUF_ALIASES) == [
        "-ac"
    ]


def test_ffuf_vhost_run_drops_both_silent_spellings():
    args = ["-of", "json", "-o", "/dev/stdout", "-s"]
    extra = ["-silent", "-s", "-ac"]
    reserved = ("-l", "-o", "-json", "-silent")
    assert merge_extra_args(args, extra, reserved, ffuf.FFUF_ALIASES) == ["-ac"]


@pytest.mark.parametrize(
    "aliases", [naabu.NAABU_ALIASES, dnsx.DNSX_ALIASES], ids=["naabu", "dnsx"]
)
def test_a_long_list_flag_cannot_replace_the_generated_input(aliases):
    extra = ["-list", "/etc/hosts", "-j", "-retry", "2"]
    reserved = ("-l", "-json", "-silent")
    assert merge_extra_args([], extra, reserved, aliases) == ["-retry", "2"]


def test_cdncheck_short_json_flag_is_not_passed_twice():
    reserved = ("-l", "-o", "-jsonl", "-silent")
    assert merge_extra_args(
        ["-resp"], ["-j", "-exclude"], reserved, cdncheck.CDNCHECK_ALIASES
    ) == ["-exclude"]


def test_urlfinder_cannot_switch_its_plain_output_to_json():
    args = ["-d", "example.com", "-all"]
    extra = ["-j", "-jsonl", "-list", "other.example", "-v"]
    reserved = ("-l", "-o", "-jsonl", "-silent")
    assert merge_extra_args(args, extra, reserved, urlfinder.URLFINDER_ALIASES) == [
        "-v"
    ]


class _Runner:
    def __init__(self, binary, **kwargs):
        self.binary = binary
        self.kwargs = kwargs


@pytest.mark.parametrize(
    ("module", "build", "aliases"),
    [
        (ffuf, lambda: ffuf.FfufClient(wordlist="w"), ffuf.FFUF_ALIASES),
        (naabu, lambda: naabu.NaabuClient(), naabu.NAABU_ALIASES),
        (dnsx, lambda: dnsx.DnsxClient(), dnsx.DNSX_ALIASES),
        (cdncheck, lambda: cdncheck.CdncheckClient(), cdncheck.CDNCHECK_ALIASES),
        (urlfinder, lambda: urlfinder.UrlfinderClient(), urlfinder.URLFINDER_ALIASES),
    ],
    ids=["ffuf", "naabu", "dnsx", "cdncheck", "urlfinder"],
)
def test_the_runner_carries_the_alias_map(monkeypatch, module, build, aliases):
    monkeypatch.setattr(module, "CLIToolRunner", _Runner)
    assert build()._runner.kwargs["aliases"] is aliases


class _Recording(_Runner):
    def run(self, **kwargs):
        self.ran = kwargs
        return SimpleNamespace(output_lines=[])


def _reserved(kwargs: dict) -> tuple[str, ...]:
    defaults = inspect.signature(CLIToolRunner.run).parameters
    return tuple(
        kwargs.get(name, defaults[name].default)
        for name in ("input_flag", "output_flag", "json_flag", "silent_flag")
    )


def test_urlfinder_collect_reserves_its_own_json_flag(monkeypatch):
    monkeypatch.setattr(urlfinder, "CLIToolRunner", _Recording)
    client = urlfinder.UrlfinderClient(extra_args=["-j", "-v"])
    client.collect("example.com")
    ran = client._runner.ran
    assert merge_extra_args(
        ran["args"], ran["extra_args"], _reserved(ran), urlfinder.URLFINDER_ALIASES
    ) == ["-v"]


@pytest.mark.parametrize(
    ("extra", "reserved", "aliases"),
    [
        (["--silent", "-ac"], ("-l", "-json", "-s"), ffuf.FFUF_ALIASES),
        (["--list", "/etc/hosts", "-ac"], ("-l", "-json"), naabu.NAABU_ALIASES),
        (["--rate-limit=9999", "-ac"], ("-rate-limit",), None),
    ],
    ids=["ffuf silent", "naabu list", "equals"],
)
def test_two_dashes_spell_the_same_flag(extra, reserved, aliases):
    assert merge_extra_args([], extra, reserved, aliases) == ["-ac"]
