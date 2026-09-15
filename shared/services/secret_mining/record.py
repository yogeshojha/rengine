"""Fingerprint and context of a value."""

from __future__ import annotations

import hashlib

from shared.definitions.secrets import CONTEXT_RADIUS, MAX_CONTEXT_LENGTH
from shared.utils.text import strip_control


def fingerprint(kind: str, value: str) -> str:
    return hashlib.sha256(f"{kind}:{value}".encode()).hexdigest()


def context(text: str, start: int, end: int) -> str:
    window = text[max(0, start - CONTEXT_RADIUS) : end + CONTEXT_RADIUS]
    return strip_control(window.replace("\r", ""))[:MAX_CONTEXT_LENGTH]
