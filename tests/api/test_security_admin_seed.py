from __future__ import annotations

import pytest

from app.config import DEFAULT_ADMIN_PASSWORD, settings
from app.utils import helpers

pytestmark = pytest.mark.api


@pytest.mark.parametrize("password", [DEFAULT_ADMIN_PASSWORD, "short", ""])
def test_the_first_admin_needs_a_real_password(monkeypatch, password):
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", password)
    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
        helpers.check_admin_password()


def test_a_generated_admin_password_is_accepted(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "f3a9c1d27be84e05")
    helpers.check_admin_password()
