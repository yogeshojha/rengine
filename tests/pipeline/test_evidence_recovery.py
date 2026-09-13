from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from shared.definitions.vulnerabilities import Protocol
from stages.vulnerability_scan.evidence import (
    RETAINS_NOTHING,
    Gap,
    dump_dir,
    read_dump,
)
from tools.nuclei.client import NucleiClient, NucleiOptions

pytestmark = pytest.mark.pipeline


def _args(**over) -> list[str]:
    return NucleiClient.args(
        SimpleNamespace(options=NucleiOptions(templates_file="templates.txt", **over))
    )


def test_only_the_protocols_that_retain_nothing_are_recovered() -> None:
    assert {Protocol.NETWORK.value, Protocol.SSL.value} == RETAINS_NOTHING
    assert Protocol.HTTP.value not in RETAINS_NOTHING


def test_the_dump_directory_is_removed() -> None:
    with dump_dir() as directory:
        assert directory.is_dir()
        (directory / "x.txt").write_text("hi", encoding="utf-8")
        kept = directory
    assert not kept.exists()


def test_read_dump_returns_the_single_exchange(tmp_path: Path) -> None:
    nested = tmp_path / "ssl"
    nested.mkdir()
    (nested / "example_com:443_weak_cipher_suites.txt").write_text(
        "Dumped SSL response for example.com:443", encoding="utf-8"
    )
    assert read_dump(tmp_path) == "Dumped SSL response for example.com:443"


def test_read_dump_is_none_when_the_run_wrote_nothing(tmp_path: Path) -> None:
    assert read_dump(tmp_path) is None


def test_a_gap_carries_every_finding_the_one_run_accounts_for() -> None:
    gap = Gap(
        template_path="/t/ssl/weak-cipher-suites.yaml",
        target="1.2.3.4:2083",
        fingerprints=("aa", "bb"),
    )
    assert len(gap.fingerprints) == 2


def test_store_resp_is_off_unless_a_directory_is_given() -> None:
    assert "-store-resp" not in _args()


def test_store_resp_is_passed_with_its_directory(tmp_path: Path) -> None:
    args = _args(store_resp_dir=str(tmp_path))
    assert "-store-resp" in args
    assert args[args.index("-store-resp-dir") + 1] == str(tmp_path)
