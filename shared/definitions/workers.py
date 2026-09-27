"""Worker queues and the compose service that consumes each."""

from __future__ import annotations

from dataclasses import dataclass

from shared.definitions.constants import (
    CRITICAL_QUEUE,
    DEFAULT_QUEUE,
    SCAN_CONTROL_QUEUE,
    SCANS_QUEUE,
)


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
