from enum import StrEnum


class RIPEStatLookupType(StrEnum):
    ANNOUNCED_PREFIXES = "announced_prefixes"
    ASN_NEIGHBOURS = "asn_neighbours"
    AS_OVERVIEW = "as_overview"
    NETWORK_INFO = "network_info"
    ABUSE_CONTACT = "abuse_contact"
    PREFIX_OVERVIEW = "prefix_overview"
    RELATED_PREFIXES = "related_prefixes"


class ASNRelationship(StrEnum):
    UPSTREAM = "upstream"
    DOWNSTREAM = "downstream"
    UNCERTAIN = "uncertain"

    @classmethod
    def from_ripestat(cls, value: str) -> "ASNRelationship":
        mapping = {
            "left": cls.UPSTREAM,
            "right": cls.DOWNSTREAM,
            "uncertain": cls.UNCERTAIN,
        }
        return mapping.get(value, cls.UNCERTAIN)


class PrefixRelationship(StrEnum):
    OVERLAP = "overlap"
    MORE_SPECIFIC = "more_specific"
    LESS_SPECIFIC = "less_specific"
