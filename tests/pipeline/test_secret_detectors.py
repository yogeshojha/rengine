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
        '<a href="http://mailto:ito.thorirmun@gmail.com">Mail</a>',
        '<a href="http://mailto:info@trivenimunrolpa.gov.np">Contact</a>',
        '<a href="https://tel:9779851012345@nepal.gov.np">Call</a>',
        '<a href="http://javascript:void0@open.example.net">x</a>',
    ],
)
def test_a_link_scheme_in_the_user_field_is_not_a_credential(link):
    sweep = find(link)
    assert _CREDENTIAL_URL not in {m.kind for m in sweep.matches}
    assert sweep.dropped[DropReason.LINK_SCHEME.value] == 1


def test_the_address_inside_a_broken_mailto_link_is_still_an_email():
    found = _kinds('<a href="http://mailto:ito.thorirmun@gmail.com">Mail</a>')
    assert found.get("email") == ["ito.thorirmun@gmail.com"]


@pytest.mark.parametrize(
    ("text", "value"),
    [
        (
            "ftp://nftp:TmV4q9rBjS7pq5p@10.27.27.187:21/backup",
            "ftp://nftp:TmV4q9rBjS7pq5p@10.27.27.187:21",
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
