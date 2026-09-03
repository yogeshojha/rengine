"""Service signatures: what to send on a port and how to read the answer back."""

from __future__ import annotations

import re
from dataclasses import dataclass

READ_LIMIT = 2048
BANNER_LIMIT = 400


@dataclass(frozen=True)
class Signature:
    service: str
    pattern: re.Pattern[bytes]
    product: str | None = None
    version_group: int | None = None
    product_group: int | None = None


# ordered: the first match wins, so put specific protocols before generic ones
SIGNATURES: tuple[Signature, ...] = (
    Signature(
        "ssh",
        re.compile(rb"^SSH-\d+\.\d+-([^\r\n]+)"),
        product_group=1,
    ),
    Signature(
        "ftp",
        re.compile(
            rb"^220[- ].*?(ProFTPD|vsftpd|Pure-FTPd|FileZilla|FTP)[ /]*([\d.]*)", re.I
        ),
        product_group=1,
        version_group=2,
    ),
    Signature(
        "smtp",
        re.compile(
            rb"^220[- ].*?(Postfix|Exim|Sendmail|Microsoft ESMTP|OpenSMTPD|Haraka)[ /]*([\d.]*)",
            re.I,
        ),
        product_group=1,
        version_group=2,
    ),
    Signature("smtp", re.compile(rb"^220[- ][^\r\n]*(?:SMTP|ESMTP)", re.I)),
    Signature("pop3", re.compile(rb"^\+OK[^\r\n]*(?:POP3|Dovecot|ready)", re.I)),
    Signature("imap", re.compile(rb"^\* OK[^\r\n]*(?:IMAP|Dovecot)", re.I)),
    Signature("redis", re.compile(rb"^\+PONG"), product="Redis"),
    Signature("redis", re.compile(rb"^-(?:NOAUTH|DENIED|ERR)"), product="Redis"),
    Signature(
        "memcached",
        re.compile(rb"^VERSION ([\d.]+)"),
        product="Memcached",
        version_group=1,
    ),
    Signature(
        "vnc", re.compile(rb"^RFB (\d{3}\.\d{3})"), product="VNC", version_group=1
    ),
    Signature(
        "mongodb",
        re.compile(rb"It looks like you are trying to access MongoDB", re.I),
        product="MongoDB",
    ),
    Signature("rdp", re.compile(rb"^\x03\x00\x00"), product="RDP"),
    Signature("telnet", re.compile(rb"^\xff[\xfb-\xfe]")),
    Signature(
        "rsync", re.compile(rb"^@RSYNCD: ([\d.]+)"), product="rsyncd", version_group=1
    ),
    Signature("mqtt", re.compile(rb"^\x20\x02")),
    Signature("http", re.compile(rb"^HTTP/\d")),
)

# what to send when the port stays silent; keyed by the port's known service
PAYLOADS: dict[str, bytes] = {
    "redis": b"PING\r\n",
    "memcached": b"version\r\n",
    "mongodb": b"GET / HTTP/1.0\r\n\r\n",
    "rdp": (
        b"\x03\x00\x00\x13\x0e\xe0\x00\x00\x00\x00\x00\x01\x00\x08\x00\x03\x00\x00\x00"
    ),
    "mqtt": b"\x10\x0c\x00\x04MQTT\x04\x02\x00\x3c\x00\x00",
}
GENERIC_PAYLOAD = b"\r\n"

_MYSQL_VERSION = re.compile(rb"^[\x0a]([\x20-\x7e]{1,40})\x00")
_PRINTABLE = re.compile(rb"[^\x09\x0a\x0d\x20-\x7e]")


def _mysql(data: bytes) -> tuple[str, str | None] | None:
    """MySQL greets with a length-prefixed handshake whose 5th byte starts the version."""
    if len(data) < 6 or data[3] != 0:  # noqa: PLR2004
        return None
    match = _MYSQL_VERSION.match(data[4:])
    if not match:
        return None
    version = match.group(1).decode("ascii", "ignore")
    return ("MySQL", version)


def readable(data: bytes) -> str | None:
    text = _PRINTABLE.sub(b".", data[:BANNER_LIMIT]).decode("ascii", "ignore").strip()
    return text or None


def identify(data: bytes, port_service: str | None) -> dict:
    """Match a raw banner against the signature table. Returns {} when nothing fits."""
    if not data:
        return {}
    mysql = _mysql(data) if port_service in ("mysql", "mariadb", None) else None
    if mysql:
        return {"service": "mysql", "product": mysql[0], "version": mysql[1]}
    for sig in SIGNATURES:
        match = sig.pattern.search(data)
        if not match:
            continue
        out: dict = {"service": sig.service}
        product = sig.product
        if sig.product_group:
            found = match.group(sig.product_group)
            if found:
                product = found.decode("ascii", "ignore").strip() or product
        if product:
            out["product"] = product[:200]
        if sig.version_group:
            version = match.group(sig.version_group)
            if version:
                out["version"] = version.decode("ascii", "ignore").strip()[:100] or None
        return out
    return {}
