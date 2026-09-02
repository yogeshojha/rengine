"""Stdlib CIDR/IP math for seed expansion (no external binary — pure arithmetic)."""

from __future__ import annotations

import ipaddress

IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network

DEFAULT_MAX_HOSTS = 4096


def parse_network(cidr: str) -> IPNetwork | None:
    """Parse a CIDR (or bare IP) into a network, host bits zeroed; None if invalid."""
    try:
        return ipaddress.ip_network(cidr.strip(), strict=False)
    except ValueError:
        return None


def _usable_count(net: IPNetwork) -> int:
    total = net.num_addresses
    if net.version == 4 and net.prefixlen < 31 and total > 2:  # noqa: PLR2004
        return total - 2
    return total


def expand_network(
    cidr: str,
    *,
    max_hosts: int = DEFAULT_MAX_HOSTS,
    skip_private: bool = False,
) -> tuple[list[str], bool]:
    """Expand a CIDR to host IPs, capped at max_hosts by even-stride sampling; returns (ips, truncated)."""
    net = parse_network(cidr)
    if net is None:
        return [], False

    total = net.num_addresses
    skip_edges = net.version == 4 and net.prefixlen < 31 and total > 2  # noqa: PLR2004
    start = 1 if skip_edges else 0
    end = total - 1 if skip_edges else total
    usable = max(end - start, 0)
    if usable == 0:
        return [str(net.network_address)], False

    truncated = usable > max_hosts
    stride = (usable // max_hosts) or 1 if truncated else 1

    ips: list[str] = []
    idx = start
    while idx < end and len(ips) < max_hosts:
        addr = net[idx]
        if not (skip_private and addr.is_private):
            ips.append(str(addr))
        idx += stride
    return ips, truncated
