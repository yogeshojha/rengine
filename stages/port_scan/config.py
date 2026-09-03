from __future__ import annotations

from pydantic import Field

from shared.definitions.ports import (
    PORT_PROFILES,
    SCAN_POLICY_LABELS,
    PortProfile,
    ScanPolicy,
)
from stages.config import StageConfig, rate, threads, timeout

_PROFILE_LABELS = {spec.key: spec.label for spec in PORT_PROFILES}
_SCAN_TYPES = {"connect": "Connect", "syn": "SYN"}


class PortScanConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Scan ports",
        description="Find listening TCP services on every address in scope.",
    )
    profile: PortProfile = Field(
        default=PortProfile.EXPOSURE,
        title="Port set",
        description="Which ports to probe. Web and sensitive covers the web surface plus admin and database ports.",
        json_schema_extra={"option_labels": _PROFILE_LABELS},
    )
    ports: str = Field(
        default="",
        max_length=2000,
        title="Custom ports",
        description="Used only when the port set is Custom. A list or range like 80,443,8000-8100.",
    )
    exclude_ports: str = Field(
        default="",
        max_length=2000,
        title="Exclude ports",
        description="Ports never to probe, as a list or range.",
    )
    scan_type: str = Field(
        default="connect",
        title="Scan type",
        description="Connect completes the TCP handshake. SYN is faster but needs raw sockets.",
        json_schema_extra={"options": list(_SCAN_TYPES), "option_labels": _SCAN_TYPES},
    )
    rate: int = rate(1000, tool="naabu", title="Packet rate (pps)")
    threads: int = threads(
        100,
        title="Concurrency",
        description="Sockets in flight. The packet rate, not this, is what the target feels.",
    )
    timeout: int = timeout(3, title="Timeout (s)")
    retries: int = Field(
        default=1,
        ge=0,
        le=5,
        title="Retries",
        description="Extra attempts per port. Every retry costs a full timeout on a filtered port.",
    )
    cdn_policy: ScanPolicy = Field(
        default=ScanPolicy.WEB,
        title="CDN-fronted addresses",
        description="A CDN edge answers for thousands of names, so a full scan there reports the CDN, not you.",
        json_schema_extra={"option_labels": SCAN_POLICY_LABELS},
    )
    scan_cloud: bool = Field(
        default=True,
        title="Scan cloud addresses in full",
        description="Cloud ranges host your own machines, unlike a CDN edge. Scan them like any other address.",
    )
    skip_private: bool = Field(
        default=True,
        title="Skip private addresses",
        description="Never probe loopback, link-local or RFC1918 addresses.",
    )
    port_threshold: int = Field(
        default=500,
        ge=0,
        le=65535,
        title="Open-port threshold",
        description="Discard a host reporting more open ports than this. It is a tarpit, not a surface. 0 disables.",
    )
    max_addresses: int = Field(
        default=8192,
        ge=1,
        le=100000,
        title="Address budget",
        description="Stop after this many addresses in one scan.",
    )
