from __future__ import annotations

import re

from pydantic import Field, field_validator

from shared.definitions.ports import (
    MAX_PORT,
    PORT_PROFILES,
    SCAN_POLICY_LABELS,
    PortProfile,
    ScanPolicy,
)
from stages.config import StageConfig, advanced

_PROFILE_LABELS = {spec.key: spec.label for spec in PORT_PROFILES}
_SCAN_TYPES = {"connect": "Connect", "syn": "SYN"}
_PORT_TOKEN = re.compile(r"(\d{1,5})(?:\s*-\s*(\d{1,5}))?")
_PORT_ERROR = "Ports are numbers or ranges from 1 to 65535, separated by commas."


def port_spec_error(value: str) -> str | None:
    if not value.strip():
        return None
    for token in value.split(","):
        match = _PORT_TOKEN.fullmatch(token.strip())
        if match is None:
            return _PORT_ERROR
        low = int(match.group(1))
        high = int(match.group(2) or low)
        if not 1 <= low <= high <= MAX_PORT:
            return _PORT_ERROR
    return None


class PortScanConfig(StageConfig):
    enabled: bool = Field(
        default=False,
        title="Scan ports",
        description="Find listening TCP services on every address in scope.",
    )
    profile: PortProfile = Field(
        default=PortProfile.EXPOSURE,
        title="Port set",
        description="Ports to probe. Web and sensitive covers the web surface plus administrative and database ports.",
        json_schema_extra={"option_labels": _PROFILE_LABELS},
    )
    ports: str = Field(
        default="",
        max_length=2000,
        title="Custom ports",
        description="Used only when the port set is Custom. A list or range like 80,443,8000-8100.",
    )
    exclude_ports: str = advanced(
        "",
        max_length=2000,
        title="Exclude ports",
        description="Ports excluded from every scan, as a list or range.",
    )
    scan_type: str = advanced(
        "connect",
        title="Scan type",
        description="Connect completes the TCP handshake. SYN needs raw sockets on the worker.",
        json_schema_extra={"options": list(_SCAN_TYPES), "option_labels": _SCAN_TYPES},
    )
    cdn_policy: ScanPolicy = advanced(
        ScanPolicy.WEB,
        title="CDN-fronted addresses",
        description="Port set for addresses attributed to a CDN or WAF.",
        json_schema_extra={"option_labels": SCAN_POLICY_LABELS},
    )
    scan_cloud: bool = advanced(
        True,
        title="Scan cloud addresses in full",
        description="Scan addresses attributed to a cloud provider with the full port set.",
    )
    skip_private: bool = advanced(
        True,
        title="Skip private addresses",
        description="Skip loopback, link-local and RFC1918 addresses. An address or netblock named as the target is scanned.",
    )
    http_on_every_port: bool = advanced(
        False,
        title="HTTP on every open port",
        description="Probe ports classed as non-web services for HTTP as well.",
    )
    max_addresses: int = advanced(
        8192,
        ge=1,
        le=100000,
        title="Address budget",
        description="Stop after this many addresses.",
    )

    @field_validator("ports", "exclude_ports")
    @classmethod
    def _valid_ports(cls, value: str) -> str:
        error = port_spec_error(value)
        if error:
            raise ValueError(error)
        return value


PORT_THRESHOLD = 500
