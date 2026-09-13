from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.scan_engine.validation import (
    _mask_global_headers,
    _mask_tool_options,
    _unmask_global_headers,
    _unmask_tool_options,
    _validate_global_headers,
    _validate_tool_options,
)

pytestmark = pytest.mark.api

_HEADERS = ["Authorization: Bearer real-token", "X-Env: staging"]
_TOOLS = {"nuclei": "-header Authorization: Bearer real-token -etags intrusive"}


def test_an_export_masks_the_credential_it_carries():
    assert _mask_global_headers(_HEADERS)[0] == "Authorization: ••••••••"
    assert "real-token" not in _mask_tool_options(_TOOLS)["nuclei"]


def test_importing_an_export_is_refused_rather_than_stored():
    with pytest.raises(HTTPException, match="Authorization"):
        _validate_global_headers(_mask_global_headers(_HEADERS))


def test_importing_masked_tool_options_is_refused():
    with pytest.raises(HTTPException, match="masked"):
        _validate_tool_options(_mask_tool_options(_TOOLS))


def test_a_header_left_masked_by_the_editor_is_restored_not_refused():
    restored = _unmask_global_headers(_mask_global_headers(_HEADERS), _HEADERS)
    _validate_global_headers(restored)
    assert restored == _HEADERS


def test_tool_options_left_masked_by_the_editor_are_restored_not_refused():
    restored = _validate_tool_options(
        _unmask_tool_options(_mask_tool_options(_TOOLS), _TOOLS)
    )
    assert restored == _TOOLS


def test_an_engine_with_no_credential_is_untouched():
    _validate_global_headers(["X-Env: staging"])
    assert _validate_tool_options({"ffuf": "-mc 200,301"}) == {"ffuf": "-mc 200,301"}
