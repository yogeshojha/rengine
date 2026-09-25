from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from stages.vhost.stage import VhostStage, host_for

pytestmark = pytest.mark.pipeline


def test_host_for_normalises() -> None:
    assert host_for("admin", "example.com") == "admin.example.com"
    assert host_for("api.staging", "example.com") == "api.staging.example.com"


def test_catch_all_drops_a_wide_match() -> None:
    # 40 of 100 candidates matched
    assert VhostStage._is_catch_all([f"h{i}" for i in range(40)], 100)


def test_a_normal_hit_rate_is_kept() -> None:
    assert not VhostStage._is_catch_all(["admin", "internal"], 100)


def test_ratio_is_not_applied_to_a_tiny_wordlist() -> None:
    # below the ratio floor
    assert not VhostStage._is_catch_all(["a", "b", "c", "d", "e"], 5)


def test_the_augmented_file_is_discarded_but_the_base_is_not(tmp_path) -> None:
    base = tmp_path / "base.txt"
    base.write_text("admin\n")
    extra = tmp_path / "extra.txt"
    extra.write_text("admin\ninternal\n")
    VhostStage._discard(extra, base)
    assert not extra.exists()
    VhostStage._discard(base, base)
    assert base.exists()


class _Scalars:
    def __init__(self, names: list[str]) -> None:
        self._names = names

    def scalars(self) -> _Scalars:
        return self

    def all(self) -> list[str]:
        return self._names


class _Session:
    def __init__(self, names: list[str]) -> None:
        self._names = names

    def execute(self, _query) -> _Scalars:
        return _Scalars(self._names)


def _stage_with_names(names: list[str]) -> VhostStage:
    stage = VhostStage.__new__(VhostStage)
    stage.session = _Session(names)
    stage.ctx = SimpleNamespace(scan_id="s")
    return stage


def test_discovered_labels_strip_the_apex() -> None:
    stage = _stage_with_names(
        [
            "admin.example.com",
            "api.staging.example.com",
            "off.other.com",
            "*.example.com",
        ]
    )
    labels = stage._discovered_labels("example.com")
    assert "admin" in labels
    assert "api.staging" in labels
    assert all("other" not in label for label in labels)
    assert all("*" not in label for label in labels)


def test_wordlist_gains_discovered_labels(tmp_path: Path) -> None:
    base = tmp_path / "vhost.txt"
    base.write_text("admin\ndev\n")
    stage = _stage_with_names(["secret.example.com", "admin.example.com"])
    path, total = stage._wordlist_with_discovered(base, "example.com")
    assert path != base
    words = set(path.read_text().split())
    assert {"admin", "dev", "secret"} <= words
    assert total == len(words)
    path.unlink()
