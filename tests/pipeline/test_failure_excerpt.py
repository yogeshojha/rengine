from __future__ import annotations

import pytest

from tools.runner.executor import failure_excerpt

pytestmark = pytest.mark.pipeline

NUCLEI_STDERR = (
    "                     __     _\n"
    "   ____  __  _______/ /__  (_)\n"
    "  / __ \\/ / / / ___/ / _ \\/ /\n"
    " / / / / /_/ / /__/ /  __/ /\n"
    "/_/ /_/\\__,_/\\___/_/\\___/_/   v3.11.1\n"
    "\n"
    "\t\tprojectdiscovery.io\n"
    "\n"
    "[ERR] Could not read nuclei-ignore file: open /root/.config/nuclei/"
    ".nuclei-ignore: no such file or directory\n"
    "[\x1b[93mWRN\x1b[0m] Excluded 1 dast template[s] (disabled as default)\n"
    "[INF] Current nuclei version: v3.11.1 (unknown)\n"
    "[INF] Targets loaded for current scan: 4\n"
    '{"duration":"0:00:00","errors":"0","hosts":"n/a"}\n'
    "[INF] Scan completed in 858ms. No results found.\n"
    "[FTL] Could not run nuclei: no templates provided for scan\n"
)


def test_the_fatal_line_is_the_reason_not_the_banner():
    assert failure_excerpt(NUCLEI_STDERR, None) == (
        "Could not run nuclei: no templates provided for scan"
    )


def test_an_error_line_wins_over_info_and_warnings():
    stderr = "[INF] Loading\n[WRN] slow resolver\n[ERR] dial tcp: connection refused\n"
    assert failure_excerpt(stderr, None) == "dial tcp: connection refused"


def test_untagged_output_keeps_the_line_that_names_the_failure():
    stderr = (
        "flag provided but not defined: -header\n"
        "Usage:\n  katana [flags]\n  -u string   target url\n"
    )
    assert failure_excerpt(stderr, None) == "flag provided but not defined: -header"


def test_ansi_codes_never_reach_the_reason():
    assert failure_excerpt("\x1b[31m[FTL]\x1b[0m bad input\n", None) == "bad input"


def test_a_banner_alone_is_no_reason():
    banner = NUCLEI_STDERR.split("[ERR]")[0]
    assert failure_excerpt(banner, None) == ""
    assert failure_excerpt(banner, "tool printed this and stopped") == (
        "tool printed this and stopped"
    )
