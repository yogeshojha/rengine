from __future__ import annotations

import time

from stages.vulnerability_scan.scanners import echo_guard


def test_a_backtracking_check_pattern_is_cut_short():
    probe = echo_guard._probe("regex", r"(a|aa)+$", fold=False)
    started = time.monotonic()
    assert probe("a" * 60 + "!") is None
    assert time.monotonic() - started < 1


def test_an_ordinary_check_pattern_still_answers():
    probe = echo_guard._probe("regex", r"root:.*:0:0:", fold=False)
    assert probe("root:x:0:0:root:/root:/bin/bash") is True
    assert probe("nothing here") is False


def test_a_slow_alignment_reads_no_bindings(monkeypatch):
    monkeypatch.setattr(echo_guard, "MATCH_SECONDS", 0.0001)
    spelled = "{{a}}x{{b}}x{{c}}x{{d}}x{{e}}y"
    assert echo_guard._align(spelled, "x" * 3000) == {}
