"""Tone vocabulary for rows, chips and events."""

from __future__ import annotations

from enum import StrEnum


class Tone(StrEnum):
    NEUTRAL = "neutral"
    SUCCESS = "success"
    WARNING = "warning"
    CRITICAL = "critical"
    INFO = "info"
    MUTED = "muted"
