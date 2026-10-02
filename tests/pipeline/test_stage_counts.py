from __future__ import annotations

import ast
from pathlib import Path

import pytest

from shared.definitions.notifications import stage_count_summary
from shared.definitions.stage_counts import (
    STAGE_COUNT_LABELS,
    UNSHOWN_COUNTS,
    stage_figures,
)
from shared.models.scan_activity import ScanActivityRead
from shared.utils.text import counted, sentences

pytestmark = pytest.mark.pipeline

_STAGES = Path(__file__).resolve().parents[2] / "stages"


def _dict_keys(node: ast.AST) -> set[str]:
    if not isinstance(node, ast.Dict):
        return set()
    return {
        k.value
        for k in node.keys
        if isinstance(k, ast.Constant) and isinstance(k.value, str)
    }


def _reported_keys() -> dict[str, set[str]]:
    """Every count key a stage module writes, by file."""
    out: dict[str, set[str]] = {}
    for path in _STAGES.rglob("*.py"):
        keys: set[str] = set()
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.keyword) and node.arg == "counts":
                keys |= _dict_keys(node.value)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "counts":
                        keys |= _dict_keys(node.value)
                    if (
                        isinstance(target, ast.Subscript)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "counts"
                        and isinstance(target.slice, ast.Constant)
                    ):
                        keys.add(target.slice.value)
        if keys:
            out[str(path.relative_to(_STAGES))] = keys
    return out


def test_every_reported_count_has_a_label():
    reported = _reported_keys()
    assert reported, "the scan found no stage counts"
    missing = {
        path: sorted(keys - STAGE_COUNT_LABELS.keys() - UNSHOWN_COUNTS)
        for path, keys in reported.items()
        if keys - STAGE_COUNT_LABELS.keys() - UNSHOWN_COUNTS
    }
    assert not missing, missing


def test_figures_follow_the_count_and_the_stage():
    figures = stage_figures(
        "takeover", {"vulnerabilities": 1, "checked": 14, "reason": "x"}
    )
    assert figures == [
        ("vulnerabilities", 1, "finding"),
        ("checked", 14, "names checked"),
    ]
    assert stage_figures("waf_detect", {"checked": 1}) == [
        ("checked", 1, "web asset checked")
    ]
    assert stage_figures("subdomain_discovery", {"excluded": 3, "subdomains": 0}) == [
        ("subdomains", 0, "web assets")
    ]


def test_notification_summary_skips_zeros_and_groups_thousands():
    assert (
        stage_count_summary({"endpoints": 1200, "endpoints_new": 0}, "url_discovery")
        == "1,200 endpoints"
    )
    assert stage_count_summary({"waf": 0}) == "no results"


def test_activity_read_carries_its_labelled_figures():
    read = ScanActivityRead.model_validate(
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "scan_id": "00000000-0000-0000-0000-000000000002",
            "name": "http_probe",
            "title": "HTTP probe",
            "status": "success",
            "result": {"http_assets": 13},
            "created_at": "2026-10-01T00:00:00Z",
        }
    )
    assert read.model_dump()["figures"] == [
        {"key": "http_assets", "value": 13, "label": "HTTP services"}
    ]


def test_warnings_read_as_sentences():
    assert (
        sentences(
            [
                f"{counted(29216, 'name')} not checked for a mail host of their own.",
                "2 names gave no MX answer",
                "",
            ]
        )
        == "29,216 names not checked for a mail host of their own. "
        "2 names gave no MX answer."
    )
