from __future__ import annotations

from types import SimpleNamespace

import pytest

from shared.definitions.tools import TOOL_NAMES
from shared.definitions.vulnerabilities import Scanner, Severity
from stages.dast_scan.scanners.dalfox import _mark_url, _marker
from tools.dalfox import DalfoxClient, DalfoxOptions, parse_finding

pytestmark = pytest.mark.pipeline

_V = {
    "type": "V",
    "type_description": "Vulnerable - act on it",
    "detection_method": "dom-verification",
    "inject_type": "inHTML",
    "method": "GET",
    "data": "https://a.example/search?q=<script>alert(1)</script>",
    "param": "q",
    "payload": "<script>alert(1)</script>",
    "evidence": "DOM verification successful",
    "cwe": "CWE-79",
    "severity": "High",
    "message_id": 606,
    "message_str": "Triggered",
}


def test_a_vulnerable_finding_maps_to_a_dalfox_row():
    finding = parse_finding(_V)
    assert finding is not None
    assert finding.scanner == Scanner.DALFOX.value
    assert finding.severity == Severity.HIGH.value
    assert finding.host == "a.example"
    assert finding.port == 443
    assert finding.cwe_ids == ["CWE-79"]
    assert finding.matcher_name == "inHTML"
    assert not finding.interaction


def test_an_oob_finding_is_proven():
    finding = parse_finding({**_V, "detection_method": "oob"})
    assert finding.interaction == {"dalfox": "oob"}


def test_the_meta_line_and_non_claims_are_skipped():
    assert parse_finding({"findings_count": 2, "total_requests": 10}) is None
    assert parse_finding({"type": "I", "cwe": "CWE-1104"}) is None
    assert parse_finding({}) is None


def test_the_finding_fingerprint_is_stable_and_scanner_scoped():
    a = parse_finding(_V)
    b = parse_finding(dict(_V))
    assert a.fingerprint == b.fingerprint
    assert (
        a.fingerprint
        != parse_finding({**_V, "data": "https://b.example/?q=1"}).fingerprint
    )


def test_the_reflection_probe_marks_every_parameter_value():
    marker = "rxdeadbeef"
    marked = _mark_url("https://a/x?id=1&name=bob", marker)
    assert marked == f"https://a/x?id={marker}&name={marker}"
    assert _mark_url("https://a/x", marker) == "https://a/x"


def test_a_fresh_marker_is_long_and_prefixed():
    assert _marker().startswith("rx")
    assert len(_marker()) >= 8


def _args(**over) -> list[str]:
    return DalfoxClient.args(SimpleNamespace(options=DalfoxOptions(**over)))


def test_the_client_streams_jsonl_and_deduplicates_nothing():
    args = _args()
    assert args[0] == "scan"
    assert args[args.index("--format") + 1] == "jsonl"
    assert args[args.index("--dedup-urls") + 1] == "off"
    assert "--skip-mining" in args
    assert "--skip-discovery" in args


def test_every_claim_type_the_parser_accepts_is_asked_for():
    args = _args()
    asked = set(args[args.index("--only-poc") + 1].split(","))
    assert asked == {"v", "r", "a"}


def test_dalfox_takes_tool_args():
    assert "dalfox" in TOOL_NAMES


def test_the_client_passes_the_blind_callback_when_set():
    args = _args(blind_url="https://oob.example")
    assert args[args.index("--blind") + 1] == "https://oob.example"
    assert "--blind" not in _args()
