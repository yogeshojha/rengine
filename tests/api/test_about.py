from __future__ import annotations

import pytest

from app.services import about as about_service
from shared.definitions.about import release_url
from shared.definitions.toolchain import TOOLCHAIN

pytestmark = pytest.mark.api


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("3.0.0", "https://github.com/yogeshojha/rengine/releases/tag/v3.0.0"),
        (
            "3.1.0-rc.1",
            "https://github.com/yogeshojha/rengine/releases/tag/v3.1.0-rc.1",
        ),
        ("unknown", None),
        ("3.0", None),
        ("3.0.0+dev", None),
    ],
)
def test_only_a_tagged_version_links_to_a_release(version, expected):
    assert release_url(version) == expected


class _DownRedis:
    async def info(self, section):
        raise ConnectionError(section)


async def test_an_unreadable_component_is_null_never_an_error(session, monkeypatch):
    monkeypatch.setattr(about_service, "async_client", _DownRedis)

    found = await about_service.about(session)

    assert found.redis is None
    assert found.postgres is not None
    assert found.postgres[0].isdigit()
    assert [tool.name for tool in found.tools] == sorted(t.name for t in TOOLCHAIN)
    assert all(tool.url.startswith("https://github.com/") for tool in found.tools)
