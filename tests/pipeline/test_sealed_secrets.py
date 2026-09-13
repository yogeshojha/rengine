from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from shared.models.types import EncryptedJSON
from shared.services.proxy_resolve import resolve_proxy_url
from shared.services.scan_resolve import seal_headers, unseal_headers
from shared.utils.crypto import (
    SecretDecryptionError,
    encrypt_secret,
    is_sealed,
)

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
    monkeypatch.setenv("SECRET_KEY", "the-key-this-instance-was-set-up-with")


def _rotate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "a-different-key")


def _proxy(endpoints_encrypted: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        name="corp", is_active=True, endpoints_encrypted=endpoints_encrypted
    )


def test_a_sealed_value_is_recognised_as_sealed():
    assert is_sealed(encrypt_secret("Bearer token"))
    assert not is_sealed("Bearer token")
    assert not is_sealed("")


def test_headers_survive_the_round_trip():
    sealed = seal_headers({"Authorization": "Bearer tok", "X-Trace": ""})
    assert unseal_headers(sealed) == {"Authorization": "Bearer tok", "X-Trace": ""}


def test_headers_written_before_sealing_are_read_as_they_are():
    assert unseal_headers({"Authorization": "Bearer tok"}) == {
        "Authorization": "Bearer tok"
    }


def test_a_header_sealed_under_another_key_is_refused(monkeypatch: pytest.MonkeyPatch):
    sealed = seal_headers({"Authorization": "Bearer tok"})
    _rotate(monkeypatch)
    with pytest.raises(SecretDecryptionError, match="Authorization"):
        unseal_headers(sealed)


def test_an_encrypted_column_survives_the_round_trip():
    column = EncryptedJSON()
    stored = column.process_bind_param({"auth_type": "bearer"}, None)
    assert column.process_result_value(stored, None) == {"auth_type": "bearer"}


def test_a_column_written_before_sealing_is_read_as_json():
    column = EncryptedJSON()
    assert column.process_result_value('{"auth_type": "basic"}', None) == {
        "auth_type": "basic"
    }


def test_a_column_sealed_under_another_key_is_refused(monkeypatch: pytest.MonkeyPatch):
    column = EncryptedJSON()
    stored = column.process_bind_param({"auth_type": "bearer"}, None)
    _rotate(monkeypatch)
    with pytest.raises(SecretDecryptionError):
        column.process_result_value(stored, None)


def test_a_proxy_survives_the_round_trip():
    sealed = encrypt_secret(json.dumps(_ENDPOINTS))
    assert resolve_proxy_url(_proxy(sealed)) == "http://u:p@10.0.0.1:8080"


def test_a_proxy_written_before_sealing_is_read_as_it_is():
    assert (
        resolve_proxy_url(_proxy(json.dumps(_ENDPOINTS))) == "http://u:p@10.0.0.1:8080"
    )


def test_a_proxy_sealed_under_another_key_is_refused(monkeypatch: pytest.MonkeyPatch):
    sealed = encrypt_secret(json.dumps(_ENDPOINTS))
    _rotate(monkeypatch)
    with pytest.raises(SecretDecryptionError, match="corp"):
        resolve_proxy_url(_proxy(sealed))
