from __future__ import annotations

import pytest

from stages.config import share_rate
from stages.vulnerability_scan.scanners.nuclei import _rate_plan
from tools.wafw00f.client import unreadable_headers

pytestmark = pytest.mark.pipeline


@pytest.mark.parametrize(
    ("rate", "processes", "each"),
    [(150, 4, 37), (150, 1, 150), (100, 2, 50), (5, 4, 1), (1, 4, 1)],
)
def test_each_process_takes_a_share_of_the_stage_budget(
    rate: int, processes: int, each: int
):
    assert share_rate(rate, processes) == each


@pytest.mark.parametrize(("rate", "processes"), [(150, 4), (100, 2), (37, 3), (9, 2)])
def test_the_processes_together_stay_inside_the_ceiling(rate: int, processes: int):
    assert share_rate(rate, processes) * processes <= rate


def test_a_single_process_gets_the_whole_budget():
    assert share_rate(150, 0) == 150


def test_one_nuclei_group_gets_the_whole_ceiling():
    assert _rate_plan(150, 5, guarded=False)[0] == 150


@pytest.mark.parametrize(("rate", "divisor"), [(150, 5), (100, 2), (60, 3)])
def test_two_nuclei_groups_share_one_ceiling(rate: int, divisor: int):
    standard, reduced = _rate_plan(rate, divisor, guarded=True)
    assert standard + reduced == rate
    assert reduced < standard


def test_the_guarded_group_keeps_the_divisor_ratio():
    standard, reduced = _rate_plan(150, 5, guarded=True)
    assert (standard, reduced) == (125, 25)
    assert standard == reduced * 5


@pytest.mark.parametrize(("rate", "divisor"), [(150, 5), (100, 2), (60, 3), (37, 4)])
def test_the_guarded_group_never_exceeds_its_own_cap(rate: int, divisor: int):
    _, reduced = _rate_plan(rate, divisor, guarded=True)
    assert reduced <= max(1, rate // divisor)


def test_a_header_wafw00f_can_read_is_not_reported():
    assert unreadable_headers({"X-Env": "staging", "Authorization": "Bearer abc"}) == []


def test_a_header_wafw00f_would_drop_is_named():
    headers = {"Cookie": "sid=1; expires=Thu, 01 Jan 1970 00:00:00 GMT", "X-Env": "a"}
    assert unreadable_headers(headers) == ["Cookie"]


def test_no_headers_reports_nothing():
    assert unreadable_headers(None) == []
