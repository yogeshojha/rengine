"""Per-tool transport (rate, concurrency, timeout) for each intensity."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum

from shared.definitions.constants import MAX_RATE, MAX_THREADS, MAX_TIMEOUT
from shared.enums.scan import Intensity


class TransportTool(StrEnum):
    HTTPX = "httpx"
    NAABU = "naabu"
    NUCLEI = "nuclei"
    KATANA = "katana"
    FFUF = "ffuf"
    DNSX = "dnsx"
    BANNER = "banner"
    JULIUS = "julius"


@dataclass(frozen=True)
class Transport:
    tool: str
    rate: int | None
    threads: int
    timeout: int
    retries: int

    def as_dict(self) -> dict:
        return asdict(self)


# (rate per second or None for unlimited, concurrency)
_NORMAL: dict[str, tuple[int | None, int]] = {
    TransportTool.HTTPX.value: (150, 150),
    TransportTool.NAABU.value: (1000, 100),
    TransportTool.NUCLEI.value: (150, 25),
    TransportTool.KATANA.value: (150, 50),
    TransportTool.FFUF.value: (150, 40),
    TransportTool.DNSX.value: (None, 30),
    TransportTool.BANNER.value: (None, 32),
    TransportTool.JULIUS.value: (150, 20),
}
_AGGRESSIVE: dict[str, tuple[int | None, int]] = {
    TransportTool.HTTPX.value: (400, 300),
    TransportTool.NAABU.value: (3000, 200),
    TransportTool.NUCLEI.value: (400, 50),
    TransportTool.KATANA.value: (300, 100),
    TransportTool.FFUF.value: (400, 80),
    TransportTool.DNSX.value: (None, 50),
    TransportTool.BANNER.value: (None, 64),
    TransportTool.JULIUS.value: (400, 40),
}
PROFILES: dict[str, dict[str, tuple[int | None, int]]] = {
    Intensity.PASSIVE.value: _NORMAL,
    Intensity.NORMAL.value: _NORMAL,
    Intensity.AGGRESSIVE.value: _AGGRESSIVE,
}

TOOL_TIMEOUT: dict[str, int] = {
    TransportTool.HTTPX.value: 10,
    TransportTool.NAABU.value: 3,
    TransportTool.NUCLEI.value: 10,
    TransportTool.KATANA.value: 15,
    TransportTool.FFUF.value: 8,
    TransportTool.DNSX.value: 5,
    TransportTool.BANNER.value: 4,
    TransportTool.JULIUS.value: 5,
}
TOOL_RETRIES: dict[str, int] = {
    TransportTool.NAABU.value: 1,
    TransportTool.NUCLEI.value: 1,
}

RATE_TOOLS: tuple[str, ...] = tuple(
    tool for tool, (rate, _) in _NORMAL.items() if rate is not None
)


def tool_threads(
    tool: str,
    intensity: str,
    *,
    thread_override: int | None = None,
) -> int:
    """The concurrency one tool runs at under this intensity, before per-stage weights."""
    base = PROFILES.get(intensity, _NORMAL).get(tool, (None, 1))[1]
    value = thread_override if thread_override is not None else base
    return _clamp(int(value), 1, MAX_THREADS)


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def tool_rate(
    tool: str,
    intensity: str,
    *,
    rate_override: int | None = None,
    ceiling: int | None = None,
) -> int | None:
    """The rate one tool runs at under this intensity, capped by the context ceiling."""
    base = PROFILES.get(intensity, _NORMAL).get(tool, (None, 1))[0]
    value = rate_override if rate_override is not None else base
    if value is None:
        return None
    if ceiling is not None:
        value = min(value, ceiling)
    return _clamp(int(value), 1, MAX_RATE)


def transport_for(
    tool: str,
    intensity: str,
    *,
    rate_weight: float = 1.0,
    thread_weight: float = 1.0,
    timeout: int | None = None,
    thread_multiplier: float = 1.0,
    timeout_multiplier: float = 1.0,
    rate_override: int | None = None,
    thread_override: int | None = None,
    ceiling: int | None = None,
) -> Transport:
    profile = PROFILES.get(intensity, _NORMAL)
    if tool not in profile:
        msg = f"{tool!r} has no transport profile."
        raise KeyError(msg)
    threads = tool_threads(tool, intensity, thread_override=thread_override)
    rate = tool_rate(tool, intensity, rate_override=rate_override, ceiling=ceiling)
    if rate is not None:
        rate = _clamp(round(rate * rate_weight) or 1, 1, MAX_RATE)
    threads = _clamp(
        round(threads * thread_weight * thread_multiplier) or 1, 1, MAX_THREADS
    )
    base_timeout = TOOL_TIMEOUT[tool] if timeout is None else timeout
    seconds = _clamp(round(base_timeout * timeout_multiplier) or 1, 1, MAX_TIMEOUT)
    return Transport(
        tool=tool,
        rate=rate,
        threads=threads,
        timeout=seconds,
        retries=TOOL_RETRIES.get(tool, 0),
    )


_OVERRIDE_FIELDS: frozenset[str] = frozenset({"rate", "threads"})


def clean_transport_overrides(raw: object) -> dict[str, dict[str, int]]:
    """Validate a per-tool rate/concurrency override map, clamped to the safe range."""
    if not raw:
        return {}
    if not isinstance(raw, dict):
        msg = "transport must be a map of tool to rate and concurrency."
        raise ValueError(msg)
    clean: dict[str, dict[str, int]] = {}
    for tool, values in raw.items():
        if tool not in RATE_TOOLS:
            msg = f"{tool!r} is not tunable."
            raise ValueError(msg)
        if not isinstance(values, dict):
            msg = f"{tool}: expected rate and concurrency."
            raise ValueError(msg)
        entry: dict[str, int] = {}
        for field, value in values.items():
            if field not in _OVERRIDE_FIELDS:
                msg = f"{tool}: unknown setting {field!r}."
                raise ValueError(msg)
            if value is None:
                continue
            try:
                number = int(value)
            except (TypeError, ValueError) as exc:
                msg = f"{tool}.{field}: not a whole number."
                raise ValueError(msg) from exc
            limit = MAX_RATE if field == "rate" else MAX_THREADS
            entry[field] = _clamp(number, 1, limit)
        if entry:
            clean[tool] = entry
    return clean


__all__ = [
    "PROFILES",
    "RATE_TOOLS",
    "TOOL_RETRIES",
    "TOOL_TIMEOUT",
    "Transport",
    "TransportTool",
    "clean_transport_overrides",
    "tool_rate",
    "tool_threads",
    "transport_for",
]
