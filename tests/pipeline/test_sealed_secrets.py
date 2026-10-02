from __future__ import annotations

import copy
import json
import uuid
from types import SimpleNamespace

import pytest

from app.services.scan import _mask_config_headers
from shared.config import base_settings
from shared.enums.api_key import APIProvider
from shared.models.api_key import APIKey
from shared.models.types import EncryptedJSON
from shared.services.api_key.async_api_key import APIKeyService
from shared.services.api_key.sync_api_key import open_key
from shared.services.bounty_providers import intigriti
from shared.services.proxy_resolve import resolve_proxy_url
from shared.services.scan_factory import build_scan_row
from shared.services.scan_resolve import (
    MASK,
    ResolvedScanConfig,
    seal_headers,
    unseal_headers,
    unseal_run_config,
)
from shared.utils.crypto import SecretDecryptionError, encrypt_secret

pytestmark = pytest.mark.pipeline

_ENDPOINTS = [
    {
        "scheme": "http",
        "host": "10.0.0.1",
        "port": 8080,
        "username": "u",
        "password": "p",
    }
]


@pytest.fixture(autouse=True)
def _key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        base_settings(), "SECRET_KEY", "the-key-this-instance-was-set-up-with"
    )


def _rotate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(base_settings(), "SECRET_KEY", "a-different-key")


def _proxy(endpoints_encrypted: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        name="corp", is_active=True, endpoints_encrypted=endpoints_encrypted
    )


def test_headers_survive_the_round_trip():
    sealed = seal_headers({"Authorization": "Bearer tok", "X-Trace": ""})
    assert unseal_headers(sealed) == {"Authorization": "Bearer tok", "X-Trace": ""}


def test_a_header_sealed_under_another_key_is_refused(monkeypatch: pytest.MonkeyPatch):
    sealed = seal_headers({"Authorization": "Bearer tok"})
    _rotate(monkeypatch)
    with pytest.raises(SecretDecryptionError, match="Authorization"):
        unseal_headers(sealed)


def test_an_encrypted_column_survives_the_round_trip():
    column = EncryptedJSON()
    stored = column.process_bind_param({"auth_type": "bearer"}, None)
    assert column.process_result_value(stored, None) == {"auth_type": "bearer"}


def test_a_column_sealed_under_another_key_is_refused(monkeypatch: pytest.MonkeyPatch):
    column = EncryptedJSON()
    stored = column.process_bind_param({"auth_type": "bearer"}, None)
    _rotate(monkeypatch)
    with pytest.raises(SecretDecryptionError):
        column.process_result_value(stored, None)


def test_a_proxy_survives_the_round_trip():
    sealed = encrypt_secret(json.dumps(_ENDPOINTS))
    assert resolve_proxy_url(_proxy(sealed)) == "http://u:p@10.0.0.1:8080"


def test_a_proxy_sealed_under_another_key_is_refused(monkeypatch: pytest.MonkeyPatch):
    sealed = encrypt_secret(json.dumps(_ENDPOINTS))
    _rotate(monkeypatch)
    with pytest.raises(SecretDecryptionError, match="corp"):
        resolve_proxy_url(_proxy(sealed))


_RUN_PROXY = "http://scanner:proxy-pass-1@10.0.0.1:8080"
_RUN_TOOLS = {"nuclei": "-H 'X-Api-Key: tool-key-123'", "ffuf": ""}


def _run_config() -> dict:
    resolved = ResolvedScanConfig(
        target_value="example.com",
        target_type="domain",
        proxy_url=_RUN_PROXY,
        tool_options=dict(_RUN_TOOLS),
    )
    scan = build_scan_row(
        resolved=resolved,
        engine=SimpleNamespace(id=uuid.uuid4(), name="Default"),
        context=None,
        target=SimpleNamespace(id=uuid.uuid4()),
        project_id=uuid.uuid4(),
        created_by=uuid.uuid4(),
    )
    return scan.execution_config


def test_a_run_stores_its_proxy_and_tool_arguments_sealed():
    stored = json.dumps(_run_config())
    assert "proxy-pass-1" not in stored
    assert "tool-key-123" not in stored


def test_a_sealed_run_opens_for_the_worker():
    opened = unseal_run_config(_run_config())
    assert opened["proxy_url"] == _RUN_PROXY
    assert opened["tool_options"] == _RUN_TOOLS


def test_a_plaintext_run_opens_unchanged():
    legacy = {"headers": {}, "proxy_url": _RUN_PROXY, "tool_options": _RUN_TOOLS}
    opened = unseal_run_config(copy.deepcopy(legacy))
    assert opened["proxy_url"] == _RUN_PROXY
    assert opened["tool_options"] == _RUN_TOOLS


def test_a_run_proxy_sealed_under_another_key_is_refused(
    monkeypatch: pytest.MonkeyPatch,
):
    config = _run_config()
    _rotate(monkeypatch)
    with pytest.raises(SecretDecryptionError, match="proxy"):
        unseal_run_config(config)


def test_the_api_masks_a_sealed_run():
    masked = _mask_config_headers(_run_config())
    assert masked["proxy_url"] == MASK
    assert masked["tool_options"] == {"nuclei": MASK, "ffuf": ""}


def _api_key(value: str) -> APIKey:
    return APIKey(provider=APIProvider.INTIGRITI, key_value=encrypt_secret(value))


def test_an_api_key_opens_under_its_own_key():
    assert open_key(_api_key("intigriti-token-1")) == "intigriti-token-1"


def test_an_api_key_sealed_under_another_key_opens_to_nothing(
    monkeypatch: pytest.MonkeyPatch,
):
    row = _api_key("intigriti-token-1")
    _rotate(monkeypatch)
    assert open_key(row) is None
    assert APIKeyService(None)._to_read(row).key_value_masked == MASK


def test_a_platform_never_receives_the_sealed_value(monkeypatch: pytest.MonkeyPatch):
    row = _api_key("intigriti-token-1")
    _rotate(monkeypatch)
    monkeypatch.setattr(intigriti, "api_key_row", lambda *_: row)
    assert intigriti.IntigritiProvider.from_session(None) is None
