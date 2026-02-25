"""RIPEstat response parsers.

Each parser takes raw JSON (the "data" dict from RIPEstat API) and returns
a typed Pydantic model. If RIPEstat changes their response format, UPDATE THIS FILE!
"""

from datetime import datetime
from typing import Any

from shared.enums.ripestat import ASNRelationship, PrefixRelationship
from shared.logging import get_logger
from tools.ripestat.models import (
    AbuseContactResponse,
    AnnouncedPrefix,
    AnnouncedPrefixesResponse,
    ASNNeighbour,
    ASNNeighboursResponse,
    ASOverviewResponse,
    NetworkInfoResponse,
    PrefixOverviewASN,
    PrefixOverviewResponse,
    RelatedPrefixEntry,
    RelatedPrefixesResponse,
)

logger = get_logger(__name__)


def _parse_asn(resource: str) -> int:
    """Extract numeric ASN from strings like 'AS23752', '23752', etc."""
    cleaned = resource.upper().replace("AS", "").strip()
    return int(cleaned)


def _detect_ip_version(prefix: str) -> int:
    return 6 if ":" in prefix else 4


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        logger.debug("Failed to parse datetime: %s", value)
        return None


def parse_announced_prefixes(
    data: dict[str, Any], asn: int
) -> AnnouncedPrefixesResponse:
    """Parse /data/announced-prefixes response.

    Expected ripestat api response as of writing this:
        {
            "prefixes": [
                {
                    "prefix": "45.116.20.0/22",
                    "timelines": [
                        {"starttime": "2026-01-27T00:00:00", "endtime": "2026-02-10T00:00:00"}
                    ]
                }
            ],
            "resource": "23752"
        }
    """
    prefixes = []
    for entry in data.get("prefixes", []):
        prefix_str = entry.get("prefix", "")
        if not prefix_str:
            continue

        # collapse timelines into first/last seen
        timelines = entry.get("timelines", [])
        first_seen = None
        last_seen = None
        for tl in timelines:
            start = _parse_datetime(tl.get("starttime"))
            end = _parse_datetime(tl.get("endtime"))
            if start and (first_seen is None or start < first_seen):
                first_seen = start
            if end and (last_seen is None or end > last_seen):
                last_seen = end

        prefixes.append(
            AnnouncedPrefix(
                prefix=prefix_str,
                ip_version=_detect_ip_version(prefix_str),
                first_seen=first_seen,
                last_seen=last_seen,
            )
        )

    return AnnouncedPrefixesResponse(asn=asn, prefixes=prefixes)


def parse_asn_neighbours(data: dict[str, Any], asn: int) -> ASNNeighboursResponse:
    """Parse /data/asn-neighbours response.

    Expected ripestat api response as of writing this:
        {
            "neighbours": [
                {"asn": 4637, "type": "left", "power": 128}
            ],
            "neighbour_counts": {"left": 5, "right": 2, "uncertain": 1}
        }
    """
    neighbours = []
    for entry in data.get("neighbours", []):
        neighbour_asn = entry.get("asn")
        if neighbour_asn is None:
            continue

        relationship = ASNRelationship.from_ripestat(entry.get("type", "uncertain"))

        neighbours.append(
            ASNNeighbour(
                asn=int(neighbour_asn),
                relationship=relationship.value,
                power=entry.get("power", 0),
            )
        )

    return ASNNeighboursResponse(asn=asn, neighbours=neighbours)


def parse_as_overview(data: dict[str, Any], asn: int) -> ASOverviewResponse:
    """Parse /data/as-overview response.

    Expected ripestat api response as of writing this:
        {
            "resource": "23752",
            "holder": "Nepal Telecommunications Corporation",
            "block": {"resource": "23552-24575", "name": "..."},
            "announced": true,
            "type": "RIR"
        }
    """
    block = data.get("block") or {}

    return ASOverviewResponse(
        asn=asn,
        holder=data.get("holder", ""),
        rir=data.get("type"),  # "RIR" isn't the RIR name, but it's what we get
        announced=data.get("announced", False),
        block_name=block.get("name"),
        block_resource=block.get("resource"),
    )


def parse_network_info(data: dict[str, Any], ip: str) -> NetworkInfoResponse:
    """Parse /data/network-info response.

    Expected ripestat api response as of writing this:
        {
            "asns": ["23752"],
            "prefix": "49.244.0.0/18"
        }
    """
    raw_asns = data.get("asns", [])
    asns = []
    for a in raw_asns:
        try:
            asns.append(int(a))
        except (ValueError, TypeError):
            logger.debug("Skipping non-numeric ASN: %s", a)

    return NetworkInfoResponse(
        ip=ip,
        prefix=data.get("prefix"),
        asns=asns,
    )


def parse_abuse_contact(data: dict[str, Any], resource: str) -> AbuseContactResponse:
    """Parse /data/abuse-contact-finder response.

    Expected ripestat api response as of writing this:
        {
            "abuse_contacts": ["abuse@ntc.net.np"],
            "authoritative_rir": "apnic"
        }
    """
    return AbuseContactResponse(
        resource=resource,
        abuse_emails=data.get("abuse_contacts", []),
        rir=data.get("authoritative_rir"),
    )


def parse_prefix_overview(data: dict[str, Any], prefix: str) -> PrefixOverviewResponse:
    """Parse /data/prefix-overview response.

    Expected ripestat api response as of writing this:
        {
            "asns": [{"asn": 23752, "holder": "Nepal Telecom"}],
            "resource": "49.244.0.0/18",
            "announced": true,
            "is_less_specific": false
        }
    """
    asns = []
    for entry in data.get("asns", []):
        asn_val = entry.get("asn")
        if asn_val is None:
            continue
        asns.append(
            PrefixOverviewASN(
                asn=int(asn_val),
                holder=entry.get("holder", ""),
            )
        )

    return PrefixOverviewResponse(
        prefix=prefix,
        asns=asns,
        is_announced=data.get("announced", False),
    )


def parse_related_prefixes(
    data: dict[str, Any], prefix: str
) -> RelatedPrefixesResponse:
    """Parse /data/related-prefixes response.

    Expected ripestat api response as of writing this:
        {
            "prefixes": [
                {
                    "prefix": "49.244.0.0/19",
                    "origin_asn": 23752,
                    "relationship": "More Specific"
                }
            ]
        }
    """
    related = []
    for entry in data.get("prefixes", []):
        rel_prefix = entry.get("prefix", "")
        if not rel_prefix:
            continue

        # normalize relationship string from API
        raw_rel = entry.get("relationship", "").lower().replace(" ", "_")
        if "more" in raw_rel:
            relationship = PrefixRelationship.MORE_SPECIFIC.value
        elif "less" in raw_rel:
            relationship = PrefixRelationship.LESS_SPECIFIC.value
        else:
            relationship = PrefixRelationship.OVERLAP.value

        origin = entry.get("origin_asn")
        origin_asn = int(origin) if origin is not None else None

        related.append(
            RelatedPrefixEntry(
                prefix=rel_prefix,
                relationship=relationship,
                origin_asn=origin_asn,
            )
        )

    return RelatedPrefixesResponse(prefix=prefix, related=related)
