from __future__ import annotations

from shared.logging import get_logger
from shared.utils.coerce import safe_str_list, strip_trailing_dot
from tools.dnsx.models import (
    DnsxCAAEntry,
    DnsxMXEntry,
    DnsxReconResponse,
    DnsxRecord,
    DnsxSOAEntry,
    DnsxSRVEntry,
)

logger = get_logger("tools.dnsx.parser")


def parse_mx_entries(raw_list: list[str] | None) -> list[DnsxMXEntry]:
    """Parse MX records from dnsx string format.

    dnsx returns MX as: ["10 mail.example.com.", "20 mail2.example.com."]
    """
    entries = []
    for raw in safe_str_list(raw_list):
        parts = raw.split(None, 1)
        if len(parts) == 2:  # noqa: PLR2004
            try:
                priority = int(parts[0])
                host = strip_trailing_dot(parts[1])
                entries.append(DnsxMXEntry(priority=priority, host=host))
            except ValueError:
                entries.append(DnsxMXEntry(priority=0, host=strip_trailing_dot(raw)))
        elif parts:
            entries.append(DnsxMXEntry(priority=0, host=strip_trailing_dot(parts[0])))
    return entries


def parse_srv_entries(raw_list: list[str] | None) -> list[DnsxSRVEntry]:
    """Parse SRV records from dnsx string format.

    dnsx returns SRV as: ["0 5 5269 xmpp-server.l.google.com."]
    Format: priority weight port target
    """
    entries = []
    for raw in safe_str_list(raw_list):
        parts = raw.split(None, 3)
        if len(parts) == 4:  # noqa: PLR2004
            try:
                entries.append(
                    DnsxSRVEntry(
                        priority=int(parts[0]),
                        weight=int(parts[1]),
                        port=int(parts[2]),
                        target=strip_trailing_dot(parts[3]),
                    )
                )
            except ValueError:
                logger.debug(f"Skipping malformed SRV record: {raw}")
        else:
            logger.debug(f"Skipping SRV record with unexpected format: {raw}")
    return entries


def parse_soa_entries(raw_list: list | None) -> list[DnsxSOAEntry]:
    """Parse SOA records from dnsx output.

    dnsx may return SOA as:
    - List of dicts: [{"name":"...", "ns":"...", ...}]
    - List of strings: ["ns.icann.org. noc.dns.icann.org. 2024010101 7200 3600 1209600 3600"]
    """
    if not raw_list:
        return []

    entries = []
    for item in raw_list:
        if isinstance(item, dict):
            entries.append(
                DnsxSOAEntry(
                    name=strip_trailing_dot(str(item.get("name", ""))),
                    ns=strip_trailing_dot(str(item.get("ns", ""))),
                    mailbox=str(item.get("mailbox", "")),
                    serial=_safe_int(item.get("serial")),
                    refresh=_safe_int(item.get("refresh")),
                    retry=_safe_int(item.get("retry")),
                    expire=_safe_int(item.get("expire")),
                    minttl=_safe_int(item.get("minttl")),
                )
            )
        elif isinstance(item, str) and item.strip():
            # String format: "ns mailbox serial refresh retry expire minttl"
            parts = item.split()
            if len(parts) >= 7:  # noqa: PLR2004
                entries.append(
                    DnsxSOAEntry(
                        ns=strip_trailing_dot(parts[0]),
                        mailbox=parts[1],
                        serial=_safe_int(parts[2]),
                        refresh=_safe_int(parts[3]),
                        retry=_safe_int(parts[4]),
                        expire=_safe_int(parts[5]),
                        minttl=_safe_int(parts[6]),
                    )
                )
            else:
                logger.debug(f"Skipping SOA with unexpected format: {item}")
    return entries


def parse_caa_entries(raw_list: list | None) -> list[DnsxCAAEntry]:
    """Parse CAA records from dnsx output.

    dnsx may return CAA as:
    - List of dicts: [{"flag": 0, "tag": "issue", "value": "letsencrypt.org"}]
    - List of strings: ["0 issue letsencrypt.org"]
    """
    if not raw_list:
        return []

    entries = []
    for item in raw_list:
        if isinstance(item, dict):
            entries.append(
                DnsxCAAEntry(
                    flag=_safe_int(item.get("flag")),
                    tag=str(item.get("tag", "")),
                    value=str(item.get("value", "")),
                )
            )
        elif isinstance(item, str) and item.strip():
            parts = item.split(None, 2)
            if len(parts) >= 3:  # noqa: PLR2004
                entries.append(
                    DnsxCAAEntry(
                        flag=_safe_int(parts[0]),
                        tag=parts[1],
                        value=parts[2],
                    )
                )
            elif len(parts) == 2:  # noqa: PLR2004
                entries.append(DnsxCAAEntry(tag=parts[0], value=parts[1]))
    return entries


def _safe_int(value) -> int:
    """Safely convert to int, defaulting to 0."""
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def parse_dnsx_record(raw: dict) -> DnsxReconResponse:
    """Parse a single raw dnsx JSON dict into a fully typed DnsxReconResponse.

    Args:
        raw: Single JSON object from dnsx JSONL output.

    Returns:
        DnsxReconResponse with all record types parsed and structured.
    """
    host = str(raw.get("host", "")).strip()
    if not host:
        msg = "dnsx record missing 'host' field"
        raise ValueError(msg)

    if isinstance(raw.get("axfr"), dict):
        raw["axfr"] = None

    record = DnsxRecord.model_validate(raw)

    return DnsxReconResponse(
        host=record.host,
        a=safe_str_list(record.a),
        aaaa=safe_str_list(record.aaaa),
        cname=[strip_trailing_dot(c) for c in safe_str_list(record.cname)],
        ns=[strip_trailing_dot(n) for n in safe_str_list(record.ns)],
        txt=safe_str_list(record.txt),
        ptr=[strip_trailing_dot(p) for p in safe_str_list(record.ptr)],
        mx=parse_mx_entries(record.mx_raw),
        srv=parse_srv_entries(record.srv_raw),
        soa=parse_soa_entries(record.soa_raw),
        caa=parse_caa_entries(record.caa_raw),
        axfr=safe_str_list(record.axfr),
        cdn=record.cdn,
        cdn_name=record.cdn_name,
        status_code=record.status_code,
        timestamp=record.timestamp,
    )


def parse_dnsx_jsonl(json_records: list[dict]) -> list[DnsxReconResponse]:
    """Parse multiple dnsx JSON records from tool runner output.

    Args:
        json_records: List of raw JSON dicts from ToolResult.json_records.

    Returns:
        List of parsed DnsxReconResponse objects.
        Invalid records are logged and skipped.
    """
    results = []
    for i, raw in enumerate(json_records):
        try:
            results.append(parse_dnsx_record(raw))
        except (ValueError, Exception) as e:
            host = raw.get("host", "unknown")
            logger.warning(f"Failed to parse dnsx record #{i} (host={host}): {e}")
    return results
