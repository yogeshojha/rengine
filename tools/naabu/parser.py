"""naabu JSONL records, reduced to the open ports a scan stores."""

from __future__ import annotations

from shared.definitions.ports import MAX_PORT


def parse_port_record(rec: dict) -> dict | None:
    """One open port, or None when the record names no address or no valid port."""
    ip = rec.get("ip") or rec.get("host")
    port = rec.get("port")
    if not ip or not isinstance(port, int) or not 0 < port <= MAX_PORT:
        return None
    return {
        "ip": str(ip),
        "port": port,
        "protocol": rec.get("protocol") or "tcp",
        "tls": bool(rec.get("tls")),
    }
