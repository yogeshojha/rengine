"""Sockets a forked child must not hold open for its parent."""

from __future__ import annotations

import os
import socket
import stat
from pathlib import Path

_FD_DIR = Path("/proc/self/fd")


def _reaches(fd: int, port: int) -> bool:
    try:
        if not stat.S_ISSOCK(os.fstat(fd).st_mode):
            return False
        sock = socket.socket(fileno=fd)
    except OSError:
        return False
    try:
        peer = sock.getpeername()
    except OSError:
        return False
    finally:
        sock.detach()
    return isinstance(peer, tuple) and peer[1] == port


def release_sockets_to(port: int) -> int:
    """Point every open socket connected to `port` at /dev/null and return how many."""
    null = os.open(os.devnull, os.O_RDWR)
    released = 0
    try:
        for entry in list(_FD_DIR.iterdir()):
            fd = int(entry.name)
            if fd != null and _reaches(fd, port):
                os.dup2(null, fd, inheritable=False)
                released += 1
    finally:
        os.close(null)
    return released
