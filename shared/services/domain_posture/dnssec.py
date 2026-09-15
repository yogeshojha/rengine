"""One DO-bit query per zone against a validating resolver."""

from __future__ import annotations

import random
import socket
import struct

from shared.definitions.domain_posture import VALIDATING_RESOLVERS, DnssecState

_TYPE_A = 1
_TYPE_DS = 43
_OPT = 41
_UDP_SIZE = 4096
_DO_BIT = 0x00008000
_FLAG_AD = 0x0020
_RCODE_MASK = 0x000F
_RCODE_SERVFAIL = 2
_RCODE_NXDOMAIN = 3
_HEADER = 12
_TIMEOUT = 2.5
_FLAG_CD = 0x0010


def _question(name: str, qtype: int) -> bytes:
    labels = [part for part in name.strip(".").split(".") if part]
    encoded = b"".join(bytes([len(label)]) + label.encode("idna") for label in labels)
    return encoded + b"\x00" + struct.pack("!HH", qtype, 1)


def _packet(name: str, qtype: int, *, checking_disabled: bool = False) -> bytes:
    flags = 0x0100 | (_FLAG_CD if checking_disabled else 0)
    header = struct.pack("!HHHHHH", random.randint(0, 65535), flags, 1, 0, 0, 1)  # noqa: S311
    opt = b"\x00" + struct.pack("!HHIH", _OPT, _UDP_SIZE, _DO_BIT, 0)
    return header + _question(name, qtype) + opt


def _ask(
    name: str, qtype: int, server: str, *, checking_disabled: bool = False
) -> tuple[int, bool, int] | None:
    """(rcode, ad, answers) or None when the resolver did not answer."""
    packet = _packet(name, qtype, checking_disabled=checking_disabled)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(_TIMEOUT)
    try:
        sock.sendto(packet, (server, 53))
        data, _ = sock.recvfrom(_UDP_SIZE)
    except OSError:
        return None
    finally:
        sock.close()
    if len(data) < _HEADER or data[:2] != packet[:2]:
        return None
    flags = struct.unpack("!H", data[2:4])[0]
    answers = struct.unpack("!H", data[6:8])[0]
    return flags & _RCODE_MASK, bool(flags & _FLAG_AD), answers


def dnssec_state(zone: str, servers: tuple[str, ...] = VALIDATING_RESOLVERS) -> str:
    """signed, unsigned, broken or unknown."""
    for server in servers:
        answer = _ask(zone, _TYPE_A, server)
        if answer is None:
            continue
        rcode, ad, _ = answer
        if rcode == _RCODE_SERVFAIL:
            plain = _ask(zone, _TYPE_A, server, checking_disabled=True)
            if plain is None or plain[0] == _RCODE_SERVFAIL:
                continue
            return DnssecState.BROKEN.value
        if ad:
            return DnssecState.SIGNED.value
        ds = _ask(zone, _TYPE_DS, server)
        if ds is None:
            continue
        ds_rcode, ds_ad, ds_answers = ds
        if ds_rcode == _RCODE_SERVFAIL:
            return DnssecState.BROKEN.value
        if ds_answers > 0 and ds_ad:
            return DnssecState.SIGNED.value
        if rcode in (0, _RCODE_NXDOMAIN):
            return DnssecState.UNSIGNED.value
    return DnssecState.UNKNOWN.value
