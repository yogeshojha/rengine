from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.scan_context import _apply_extra_headers_update
from app.services.scan_engine.validation import (
    _mask_global_headers,
    _mask_tool_options,
    _unmask_global_headers,
    _unmask_tool_options,
    _validate_global_headers,
    _validate_tool_options,
)
from shared.models.scan_context import AuthHeader, ScanContextUpdate
from shared.services.scan_resolve import MASK, _mask_headers, redact_message
from tools.httpx.parser import _redact_request

pytestmark = pytest.mark.api

_HEADERS = ["Authorization: Bearer real-token", "X-Env: staging"]
_TOOLS = {"nuclei": "-header Authorization: Bearer real-token -etags intrusive"}
_CREDENTIALS = [
    "Proxy-Authorization",
    "X-Goog-Api-Key",
    "Api-Key",
    "apikey",
    "X-Session-Id",
    "Ocp-Apim-Subscription-Key",
    "X-Access-Key",
    "X-Password",
]
_READABLE = ["Access-Control-Allow-Credentials", "WWW-Authenticate", "X-Env"]


@pytest.mark.parametrize("name", _CREDENTIALS)
def test_a_credential_header_is_masked_on_every_surface(name):
    raw = f"GET / HTTP/1.1\r\nHost: x\r\n{name}: s3cret\r\n\r\n"
    assert _mask_headers([{"name": name, "value": "s3cret"}])[0]["value"] == MASK
    assert _mask_global_headers([f"{name}: s3cret"]) == [f"{name}: {MASK}"]
    assert "s3cret" not in redact_message(raw)
    assert "s3cret" not in _redact_request(raw)


@pytest.mark.parametrize("name", _READABLE)
def test_a_plain_header_stays_readable(name):
    assert _mask_headers([{"name": name, "value": "true"}])[0]["value"] == "true"
    assert f"{name}: true" in redact_message(f"HTTP/1.1 200 OK\r\n{name}: true\r\n\r\n")


def test_a_masked_context_header_sent_back_keeps_the_stored_value():
    stored = [{"name": "X-Goog-Api-Key", "value": "AIza-real"}]
    ctx = SimpleNamespace(extra_headers=stored)
    shown = [AuthHeader(**h) for h in _mask_headers(stored)]
    _apply_extra_headers_update(ctx, ScanContextUpdate(extra_headers=shown))
    assert ctx.extra_headers == stored


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


_KEYED = {"nuclei": '-H "Authorization: Bearer SECRET" -itoken TOKEN'}
_PROXIED = {"nuclei": "-proxy http://user:pw@proxy:8080 -itoken abc123"}


def test_a_masked_flag_takes_the_value_stored_behind_the_same_flag():
    restored = _unmask_tool_options({"nuclei": f"-itoken {MASK}"}, _KEYED)
    assert restored == {"nuclei": "-itoken TOKEN"}


def test_reordered_masked_values_each_return_behind_their_own_flag():
    submitted = {"nuclei": f'-itoken {MASK} -H "Authorization: {MASK}"'}
    assert _unmask_tool_options(submitted, _KEYED) == {
        "nuclei": '-itoken TOKEN -H "Authorization: Bearer SECRET"'
    }


def test_proxy_credentials_and_a_token_round_trip():
    restored = _validate_tool_options(
        _unmask_tool_options(_mask_tool_options(_PROXIED), _PROXIED)
    )
    assert restored == _PROXIED


def test_a_stored_proxy_credential_is_not_moved_to_another_host():
    submitted = {"nuclei": f"-u http://{MASK}@evil.com"}
    restored = _unmask_tool_options(submitted, _PROXIED)
    assert restored == submitted
    with pytest.raises(HTTPException) as exc:
        _validate_tool_options(restored)
    assert exc.value.status_code == 400
