from __future__ import annotations

import pytest
from pydantic import ValidationError

from shared.definitions.toolbox import MAX_TOOL_INPUT_BYTES, ToolRunRequest


def test_input_within_bound_is_accepted():
    request = ToolRunRequest(tool="whois", input={"query": "example.com"})
    assert request.input == {"query": "example.com"}


def test_input_over_bound_is_refused():
    with pytest.raises(ValidationError, match="larger than 16 KB"):
        ToolRunRequest(tool="whois", input={"query": "a" * MAX_TOOL_INPUT_BYTES})
