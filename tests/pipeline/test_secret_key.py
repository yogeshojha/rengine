from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings
from shared.config import PUBLISHED_SECRET_KEY, BaseAppSettings, base_settings
from shared.utils.crypto import encrypt_secret

pytestmark = pytest.mark.pipeline

GENERATED = "0" * 64


def _base(**values) -> BaseAppSettings:
    return BaseAppSettings(_env_file=None, **values)


@pytest.mark.parametrize("key", [PUBLISHED_SECRET_KEY, "short-key"])
def test_every_process_refuses_a_weak_key_in_production(key):
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        _base(SECRET_KEY=key, DEBUG=False)


def test_a_generated_key_is_accepted():
    assert _base(SECRET_KEY=GENERATED, DEBUG=False).SECRET_KEY == GENERATED


@pytest.mark.parametrize("debug", [True, False])
def test_the_api_refuses_an_empty_key(debug):
    with pytest.raises(ValidationError, match="SECRET_KEY is not set"):
        Settings(_env_file=None, SECRET_KEY="", DEBUG=debug, ADMIN_PASSWORD="x")


def test_nothing_is_sealed_without_a_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(base_settings(), "SECRET_KEY", "")
    with pytest.raises(RuntimeError, match="SECRET_KEY is not set"):
        encrypt_secret("value")
