"""Out-of-band testing: the server a callback reaches, and how long a batch waits for it."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

OAST_TAG = "oast"

# nuclei refuses the request outright when these have no client behind them
INTERACTSH_RE = re.compile(r"interactsh[-_](?:url|protocol|request|response|ip)", re.I)


def needs_callback(raw: str | None, tags: Iterable[str] | None = None) -> bool:
    """Whether a check cannot run without an out-of-band server."""
    if raw and INTERACTSH_RE.search(raw):
        return True
    return OAST_TAG in {str(t).lower() for t in tags or ()}


class OastMode(StrEnum):
    OFF = "off"
    SELF_HOSTED = "self_hosted"
    PUBLIC = "public"


OAST_MODE_LABELS: dict[str, str] = {
    OastMode.OFF.value: "Off",
    OastMode.SELF_HOSTED.value: "Self-hosted",
    OastMode.PUBLIC.value: "Public",
}

OAST_MODE_HELP: dict[str, str] = {
    OastMode.OFF.value: "Checks that need a callback are skipped.",
    OastMode.SELF_HOSTED.value: (
        "An interactsh server this instance operates. Callbacks reach that server."
    ),
    OastMode.PUBLIC.value: (
        "The interact.sh servers ProjectDiscovery operates. A callback reaches a third party."
    ),
}

# nuclei rotates these when no server is named
PUBLIC_SERVERS: tuple[str, ...] = (
    "oast.pro",
    "oast.live",
    "oast.site",
    "oast.online",
    "oast.fun",
    "oast.me",
)

PUBLIC_ACK = (
    "Callbacks reach interact.sh, operated by ProjectDiscovery. A payload can make a "
    "target send environment variables, instance metadata or credentials with the callback."
)

DEFAULT_WAIT_SECONDS = 60
MIN_WAIT_SECONDS = 0
MAX_WAIT_SECONDS = 900
# nuclei holds a pending request this much longer than it waits
EVICTION_SLACK = 120
# an out-of-band batch sweeps for longer, so the wait is paid fewer times
OAST_BATCH_SECONDS = 1800
MAX_SERVER_LENGTH = 200

# ---------- the callback a finding carries ----------

INTERACTION_LABELS: dict[str, str] = {
    "protocol": "Channel",
    "remote-address": "Source",
    "timestamp": "Received",
    "full-id": "Callback host",
    "unique-id": "Callback host",
    "q-type": "Record",
}

INTERACTION_RAW_LABELS: dict[str, str] = {
    "raw-request": "Callback request",
    "raw-response": "Callback response",
}

INTERACTION_META: tuple[str, ...] = tuple(INTERACTION_LABELS)
INTERACTION_RAW: tuple[str, ...] = tuple(INTERACTION_RAW_LABELS)


def bare_interaction(interaction: dict | None) -> dict:
    """The callback's identity without the exchange it carried."""
    return {k: v for k, v in (interaction or {}).items() if k in INTERACTION_META}


_HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9-]{1,63})+$")
_SCHEMES = ("http://", "https://")


def normalize_server(value: str | None) -> str | None:
    """The bare host nuclei takes, or None when the value is not a host."""
    raw = (value or "").strip().lower()
    if not raw:
        return None
    for scheme in _SCHEMES:
        if raw.startswith(scheme):
            raw = raw[len(scheme) :]
            break
    raw = raw.split("/", 1)[0].strip().rstrip(".")
    if len(raw) > MAX_SERVER_LENGTH or not _HOST_RE.match(raw):
        return None
    return raw


@dataclass(frozen=True)
class OastConfig:
    """What the scanners need to reach the server, resolved once."""

    mode: str = OastMode.OFF.value
    server: str | None = None
    token: str | None = None
    wait_seconds: int = DEFAULT_WAIT_SECONDS
    reason: str | None = None

    @property
    def enabled(self) -> bool:
        return self.mode != OastMode.OFF.value


def off_reason(mode: str, *, server: str | None, acknowledged: bool) -> str | None:
    """Why the configured mode cannot be used, or None when it can."""
    if mode == OastMode.OFF.value:
        return "Out-of-band testing is off for this instance."
    if mode == OastMode.SELF_HOSTED.value and not server:
        return "No self-hosted server is set."
    if mode == OastMode.PUBLIC.value and not acknowledged:
        return "The public server has not been accepted."
    return None


__all__ = [
    "DEFAULT_WAIT_SECONDS",
    "EVICTION_SLACK",
    "INTERACTION_LABELS",
    "INTERACTION_META",
    "INTERACTION_RAW",
    "INTERACTION_RAW_LABELS",
    "INTERACTSH_RE",
    "MAX_SERVER_LENGTH",
    "MAX_WAIT_SECONDS",
    "MIN_WAIT_SECONDS",
    "OAST_BATCH_SECONDS",
    "OAST_MODE_HELP",
    "OAST_MODE_LABELS",
    "OAST_TAG",
    "PUBLIC_ACK",
    "PUBLIC_SERVERS",
    "OastConfig",
    "OastMode",
    "bare_interaction",
    "needs_callback",
    "normalize_server",
    "off_reason",
]
