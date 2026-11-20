from __future__ import annotations

import pytest

from app.api.deps import get_current_superuser
from app.api.v1 import remote_control
from tests.api.route_table import calls

pytestmark = pytest.mark.api


def _needs_superuser(path: str) -> bool:
    route = next(
        r
        for r in remote_control.router.routes
        if r.path.endswith(path) and "GET" in r.methods
    )
    return get_current_superuser in calls(route.dependant)


def test_the_chat_call_log_is_superuser_only():
    assert _needs_superuser("/channels/{channel}/calls")


def test_status_and_commands_stay_open():
    assert not _needs_superuser("/channels/{channel}/status")
    assert not _needs_superuser("/channels/{channel}/commands")
