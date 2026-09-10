"""The two nuclei rate groups run together, and only the stage thread writes."""

from __future__ import annotations

import threading
import time
import uuid

import pytest

from shared.definitions.vulnerabilities import Scanner
from stages.vulnerability_scan.config import VulnerabilityScanConfig
from stages.vulnerability_scan.scanners.base import (
    Coverage,
    ScannerContext,
    ScannerResult,
)
from stages.vulnerability_scan.scanners.nuclei import NucleiScanner

pytestmark = pytest.mark.pipeline


class _Writes:
    """Records what was stored and which thread stored it."""

    def __init__(self):
        self.threads: set[str] = set()
        self.stored: list = []

    def __call__(self, batch: list) -> int:
        self.threads.add(threading.current_thread().name)
        self.stored.extend(batch)
        return len(batch)


def _scanner(writes: _Writes) -> NucleiScanner:
    ctx = ScannerContext(
        session=None,
        scan_id=uuid.uuid4(),
        target_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        cfg=VulnerabilityScanConfig(),
        resolved=None,
        net=None,
        surface=None,
        selection=None,
        on_findings=writes,
    )
    return NucleiScanner(ctx)


def _fake_group(hold: float, findings: int):
    """Stands in for one nuclei process: emits findings from a worker thread."""

    def run(
        self, label, targets, rate, listing, selected, custom, result, missing, store
    ):
        coverage = Coverage(group=label)
        deadline = time.monotonic() + hold
        sent = 0
        while sent < findings:
            store(coverage, [f"{label}-{sent}"])
            sent += 1
            time.sleep(hold / max(findings, 1))
        while time.monotonic() < deadline:
            time.sleep(0.01)
        return coverage

    return run


async def test_both_groups_run_and_every_finding_is_stored(monkeypatch):
    writes = _Writes()
    scanner = _scanner(writes)
    monkeypatch.setattr(NucleiScanner, "_one", _fake_group(0.2, 5))

    plan = [("Standard rate", ["a"], 150), ("Reduced rate", ["b"], 50)]
    result = scanner._run_together(plan, None, 10, 0, 0, _result())

    assert len(writes.stored) == 10
    assert result.findings == 10
    assert {c.group for c in result.coverage} == {"Standard rate", "Reduced rate"}
    assert {c.findings for c in result.coverage} == {5}


async def test_only_the_calling_thread_writes(monkeypatch):
    """The Session is not thread-safe; a finding is handed over, never stored in place."""
    writes = _Writes()
    scanner = _scanner(writes)
    monkeypatch.setattr(NucleiScanner, "_one", _fake_group(0.2, 4))

    plan = [("Standard rate", ["a"], 150), ("Reduced rate", ["b"], 50)]
    scanner._run_together(plan, None, 10, 0, 0, _result())

    assert writes.threads == {threading.current_thread().name}


async def test_they_overlap_rather_than_queue(monkeypatch):
    writes = _Writes()
    scanner = _scanner(writes)
    monkeypatch.setattr(NucleiScanner, "_one", _fake_group(0.5, 2))

    plan = [("Standard rate", ["a"], 150), ("Reduced rate", ["b"], 50)]
    started = time.monotonic()
    scanner._run_together(plan, None, 10, 0, 0, _result())
    elapsed = time.monotonic() - started

    assert elapsed < 0.9, "two 0.5s groups run together, not one after the other"


async def test_a_broken_group_does_not_cost_the_other_its_coverage(monkeypatch):
    writes = _Writes()
    scanner = _scanner(writes)

    def run(
        self, label, targets, rate, listing, selected, custom, result, missing, store
    ):
        if label == "Reduced rate":
            msg = "nuclei fell over"
            raise RuntimeError(msg)
        store(Coverage(group=label), ["only-one"])
        return Coverage(group=label)

    monkeypatch.setattr(NucleiScanner, "_one", run)
    outcome = _result()

    plan = [("Standard rate", ["a"], 150), ("Reduced rate", ["b"], 50)]
    with pytest.raises(RuntimeError, match="fell over"):
        scanner._run_together(plan, None, 10, 0, 0, outcome)

    assert [c.group for c in outcome.coverage] == ["Standard rate"]
    assert writes.stored == ["only-one"]


def _result():
    return ScannerResult()


def test_the_scanner_is_registered_under_its_enum_name():
    assert NucleiScanner.name == Scanner.NUCLEI.value
