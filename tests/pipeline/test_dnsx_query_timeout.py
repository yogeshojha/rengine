"""The resolver's per-query timeout is the transport's, as a go duration."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tools.dnsx.client import DnsxClient

pytestmark = pytest.mark.pipeline


def _base(**over) -> list[str]:
    fields = {"retry": 3, "threads": 30, "resolvers": None, "query_timeout": None}
    fields.update(over)
    return DnsxClient._build_base_args(SimpleNamespace(**fields))


def test_the_query_timeout_is_a_go_duration():
    args = _base(query_timeout=5)
    assert args[args.index("-timeout") + 1] == "5s"


def test_no_query_timeout_leaves_dnsx_on_its_default():
    assert "-timeout" not in _base()


def test_threads_and_retries_still_reach_dnsx():
    args = _base(query_timeout=10)
    assert args[args.index("-t") + 1] == "30"
    assert args[args.index("-retry") + 1] == "3"
