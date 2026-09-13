from __future__ import annotations

import zipfile

import pytest

from shared.definitions.vulnerabilities import (
    DAST_ROOT,
    EXCLUDED_TAGS,
    WEAK_MATCHER_PATHS,
)
from shared.services.vuln_templates import _extract
from stages.vulnerability_scan.scanners.base import Coverage
from stages.vulnerability_scan.scanners.nuclei import _note_gaps, _unloaded
from tools.nuclei.client import _drop_record

pytestmark = pytest.mark.pipeline

# read off https://api.pdtm.sh/api/v1/tools/nuclei/ignore on 2026-09-13
IGNORE_TAGS = {"dos", "local", "fuzz", "bruteforce", "txt-service"}
IGNORE_FILE_COUNT = 14


def test_ignore_list_matches_the_measured_one() -> None:
    assert EXCLUDED_TAGS == IGNORE_TAGS
    assert len(WEAK_MATCHER_PATHS) == IGNORE_FILE_COUNT
    assert "dast/vulnerabilities/sqli/time-based-sqli.yaml" in WEAK_MATCHER_PATHS


def test_dast_root_is_a_prefix() -> None:
    assert DAST_ROOT.endswith("/")


@pytest.mark.parametrize(
    ("selected", "loaded", "expected"),
    [(6218, 6170, 48), (6182, 6182, 0), (None, 10, 0), (10, None, 0), (10, 12, 0)],
)
def test_unloaded_counts_only_a_real_shortfall(selected, loaded, expected) -> None:
    coverage = Coverage(group="Standard rate")
    coverage.templates_selected = selected
    coverage.templates_loaded = loaded
    assert _unloaded(coverage) == expected


def test_unloaded_checks_are_reported_as_partial() -> None:
    coverage = Coverage(group="Standard rate")
    coverage.templates_selected = 6218
    coverage.templates_loaded = 6170
    _note_gaps(coverage, missing=0, budget_hit=False)
    assert coverage.status == "partial"
    assert "48 selected checks did not load" in (coverage.error or "")


def test_a_full_load_reports_nothing() -> None:
    coverage = Coverage(group="Standard rate")
    coverage.templates_selected = 6182
    coverage.templates_loaded = 6182
    _note_gaps(coverage, missing=0, budget_hit=False)
    assert coverage.error is None


def test_a_suppressed_honeypot_is_recorded_as_a_dropped_host() -> None:
    line = "[WRN] Potential honeypot detected: 10.0.0.1 (matched 37 distinct templates)"
    record = _drop_record(line)
    assert record == {
        "host": "10.0.0.1",
        "reason": "flagged as a honeypot, matching 37 distinct checks. Findings suppressed.",
    }


def test_an_unresponsive_host_still_parses() -> None:
    line = (
        "[INF] Skipped 127.0.0.1:1 from target list as found unresponsive "
        'permanently: cause="port closed or filtered"'
    )
    record = _drop_record(line)
    assert record is not None
    assert record["host"] == "127.0.0.1:1"


def test_an_unrelated_line_is_not_a_drop() -> None:
    assert _drop_record("[INF] Templates loaded for current scan: 6182") is None


def _archive(path, entries: dict[str, str]):
    with zipfile.ZipFile(path, "w") as bundle:
        for name, body in entries.items():
            bundle.writestr(name, body)
    return path


def test_payload_files_are_extracted_beside_the_checks(tmp_path) -> None:
    archive = _archive(
        tmp_path / "t.zip",
        {
            "nuclei-templates/http/cves/CVE-1.yaml": "id: a\n",
            "nuclei-templates/helpers/wordlists/numbers.txt": "1\n2\n",
            "nuclei-templates/helpers/payloads/citrix_paddings.txt": "aa\n",
            "nuclei-templates/workflows/w.yaml": "id: w\n",
            "nuclei-templates/profiles/p.yaml": "id: p\n",
        },
    )
    destination = tmp_path / "official"
    written = _extract(archive, destination)

    assert written == 1
    assert (destination / "http/cves/CVE-1.yaml").is_file()
    assert (destination / "helpers/wordlists/numbers.txt").is_file()
    assert (destination / "helpers/payloads/citrix_paddings.txt").is_file()
    assert not (destination / "workflows").exists()
    assert not (destination / "profiles").exists()
