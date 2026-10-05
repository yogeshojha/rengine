"""Source IP of a scan run: the address its traffic reached the internet from."""

from __future__ import annotations

from enum import StrEnum

SERVICE_NAME = "Cloudflare"
TIMEOUT_SECONDS = 5.0


class SourceIpState(StrEnum):
    OFF = "off"
    MEASURED = "measured"


class SourceIpPhase(StrEnum):
    START = "start"
    END = "end"


class AddressFamily(StrEnum):
    IPV4 = "ipv4"
    IPV6 = "ipv6"


class SourceIpFailure(StrEnum):
    TIMEOUT = "timeout"
    PROXY = "proxy"
    UNREACHABLE = "unreachable"
    NO_ADDRESS = "no_address"
    PROXY_UNREADABLE = "proxy_unreadable"


PHASE_ORDER: tuple[str, ...] = tuple(p.value for p in SourceIpPhase)
FAMILY_ORDER: tuple[str, ...] = tuple(f.value for f in AddressFamily)

TRACE_URLS: dict[str, str] = {
    AddressFamily.IPV4.value: "https://1.1.1.1/cdn-cgi/trace",
    AddressFamily.IPV6.value: "https://[2606:4700:4700::1111]/cdn-cgi/trace",
}

FAILURE_LABELS: dict[str, str] = {
    SourceIpFailure.TIMEOUT.value: (
        f"{SERVICE_NAME} did not answer within {TIMEOUT_SECONDS:g} seconds."
    ),
    SourceIpFailure.PROXY.value: "The scan's proxy did not complete the lookup.",
    SourceIpFailure.UNREACHABLE.value: f"{SERVICE_NAME} was unreachable.",
    SourceIpFailure.NO_ADDRESS.value: f"{SERVICE_NAME} returned no address.",
    SourceIpFailure.PROXY_UNREADABLE.value: "The proxy on this run could not be read.",
}
