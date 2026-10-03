from __future__ import annotations

import subprocess
import sys

import pytest

pytestmark = pytest.mark.pipeline

_CHILD = """
import os
import socket

from shared.config import base_settings
from shared.utils.fork import release_sockets_to

settings = base_settings()
broker = socket.create_connection((settings.REDIS_HOST, settings.REDIS_PORT), timeout=5)
database = socket.create_connection(
    (settings.POSTGRES_HOST, settings.POSTGRES_PORT), timeout=5
)
released = release_sockets_to(settings.REDIS_PORT)
print(released)
print(os.readlink(f"/proc/self/fd/{broker.fileno()}"))
print(os.readlink(f"/proc/self/fd/{database.fileno()}").split(":")[0])
print(release_sockets_to(settings.REDIS_PORT))
"""


def test_a_process_lets_go_of_its_broker_sockets_and_nothing_else():
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", _CHILD],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["1", "/dev/null", "socket", "0"]
