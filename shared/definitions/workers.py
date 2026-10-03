"""Worker queues and the compose service that consumes each."""

from __future__ import annotations

from dataclasses import dataclass

from shared.definitions.constants import (
    CRITICAL_QUEUE,
    DEFAULT_QUEUE,
    SCAN_CONTROL_QUEUE,
    SCANS_QUEUE,
)

INSPECT_TIMEOUT = 1.0

# the file each worker touches and the compose healthcheck reads
HEARTBEAT_PATH = "/tmp/worker-heartbeat"  # noqa: S108
HEARTBEAT_SECONDS = 30.0
# seconds a worker stays up after it left the running state
STOPPED_GRACE_SECONDS = 60.0


@dataclass(frozen=True)
class QueueSpec:
    name: str
    label: str
    service: str


QUEUES: tuple[QueueSpec, ...] = (
    QueueSpec(SCAN_CONTROL_QUEUE, "Scan control", "worker-control"),
    QueueSpec(SCANS_QUEUE, "Scan stages", "worker-scans"),
    QueueSpec(DEFAULT_QUEUE, "Background jobs", "worker-default"),
    QueueSpec(CRITICAL_QUEUE, "Toolbox", "worker-default"),
)
