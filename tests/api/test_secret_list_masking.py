from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.services.secret import SecretService, masked_value
from shared.services.scan_resolve import MASK
from shared.utils.datetime import utc_now

pytestmark = pytest.mark.api

VALUE = "AKIA" + "IOSFODNN7EXAMPLE"


def _row(value: str = VALUE) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        scan_id=uuid.uuid4(),
        target_id=uuid.uuid4(),
        fingerprint="f" * 16,
        kind="aws_access_key",
        group="cloud",
        vendor="AWS",
        state="exposed",
        is_secret=True,
        value=value,
        subject=None,
        meta={},
        host="app.example.com",
        url="https://app.example.com/main.js",
        http_asset_id=None,
        source="body",
        sightings=1,
        hosts=1,
        discovered_at=utc_now(),
    )


def test_masked_value_keeps_a_short_prefix():
    assert masked_value(VALUE) == f"AKIA{MASK}"
    assert masked_value("abc") == MASK
    assert masked_value("-----BEGIN KEY-----\nsecretbody") == f"----{MASK}"


def test_list_read_masks_the_value():
    service = SecretService(session=None)
    read = service._to_read(_row(), target_value=None, is_new=False, masked=True)
    assert MASK in read.value
    assert VALUE not in read.value


def test_detail_read_keeps_the_value():
    service = SecretService(session=None)
    read = service._to_read(_row(), target_value=None, is_new=False)
    assert read.value == VALUE
