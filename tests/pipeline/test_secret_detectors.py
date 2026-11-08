from __future__ import annotations

import pytest

from shared.definitions.secrets import DropReason
from shared.services.secret_mining.detectors import find

pytestmark = pytest.mark.pipeline

_CREDENTIAL_URL = "credential_url"


def _kinds(text: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for match in find(text).matches:
        found.setdefault(match.kind, []).append(match.value)
    return found


@pytest.mark.parametrize(
    "link",
    [
        '<a href="http://mailto:office.ward@municipality.example">Mail</a>',
        '<a href="http://mailto:info@municipality.example">Contact</a>',
        '<a href="https://tel:15555550100@phone.example">Call</a>',
        '<a href="http://javascript:void0@open.example.net">x</a>',
    ],
)
def test_a_link_scheme_in_the_user_field_is_not_a_credential(link):
    sweep = find(link)
    assert _CREDENTIAL_URL not in {m.kind for m in sweep.matches}
    assert sweep.dropped[DropReason.LINK_SCHEME.value] == 1


def test_the_address_inside_a_broken_mailto_link_is_still_an_email():
    found = _kinds('<a href="http://mailto:office.ward@municipality.example">Mail</a>')
    assert found.get("email") == ["office.ward@municipality.example"]


@pytest.mark.parametrize(
    ("text", "value"),
    [
        (
            "ftp://user:Rk7vQ2mWx9Lp@192.0.2.10:21/backup",
            "ftp://user:Rk7vQ2mWx9Lp@192.0.2.10:21",
        ),
        (
            'fetch("https://deploy:Gh7kQ2xLp9vZ@registry.acme-corp.io/v2/")',
            "https://deploy:Gh7kQ2xLp9vZ@registry.acme-corp.io",
        ),
        (
            "sftp://mailroom:Zq8vN3pLx7Rt@files.acme-corp.io",
            "sftp://mailroom:Zq8vN3pLx7Rt@files.acme-corp.io",
        ),
    ],
)
def test_a_real_credential_url_is_still_reported(text, value):
    found = _kinds(text)
    assert found.get(_CREDENTIAL_URL) == [value]
