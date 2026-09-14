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
}
_AGGRESSIVE: dict[str, tuple[int | None, int]] = {
    TransportTool.HTTPX.value: (400, 300),
    TransportTool.NAABU.value: (3000, 200),
    TransportTool.NUCLEI.value: (400, 50),
    TransportTool.KATANA.value: (300, 100),
    TransportTool.FFUF.value: (400, 80),
    TransportTool.DNSX.value: (None, 50),
    TransportTool.BANNER.value: (None, 64),
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
}
TOOL_RETRIES: dict[str, int] = {
    TransportTool.NAABU.value: 1,
    TransportTool.NUCLEI.value: 1,
}

RATE_TOOLS: tuple[str, ...] = tuple(
    tool for tool, (rate, _) in _NORMAL.items() if rate is not None
)

INTENSITY_LABELS: dict[str, str] = {
    Intensity.PASSIVE.value: "Passive",
    Intensity.NORMAL.value: "Normal",
    Intensity.AGGRESSIVE.value: "Aggressive",
}
INTENSITY_HELP: dict[str, str] = {
    Intensity.PASSIVE.value: "Public sources only. No traffic is sent to the target.",
    Intensity.NORMAL.value: "150 requests per second per tool, 1,000 packets per second for the port scan.",
    Intensity.AGGRESSIVE.value: "400 requests per second per tool, 3,000 packets per second for the port scan. Concurrency doubled.",
}


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def tool_rate(
    tool: str,
    intensity: str,
    *,
    rate_override: int | None = None,
    ceiling: int | None = None,
) -> int | None:
    """The rate one tool runs at under this intensity, after the context's say."""
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
    ceiling: int | None = None,
) -> Transport:
    profile = PROFILES.get(intensity, _NORMAL)
    if tool not in profile:
        msg = f"{tool!r} has no transport profile."
        raise KeyError(msg)
    _, threads = profile[tool]
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


__all__ = [
    "INTENSITY_HELP",
    "INTENSITY_LABELS",
    "PROFILES",
    "RATE_TOOLS",
    "TOOL_RETRIES",
    "TOOL_TIMEOUT",
    "Transport",
    "TransportTool",
    "tool_rate",
    "transport_for",
]
