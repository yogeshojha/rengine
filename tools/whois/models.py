from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from shared.enums.whois import WhoisLookupType


class WhoisAddress(BaseModel):
    po_box: str = ""
    ext_address: str = ""
    street_address: str = ""
    locality: str = ""
    region: str = ""
    postal_code: str = ""
    country: str = ""


class WhoisEntity(BaseModel):
    handle: str = ""
    name: str = ""
    email: str = ""
    tel: str = ""
    type: str = ""
    url: str = ""
    rir: str = ""
    whois_server: str = ""
    address: WhoisAddress | None = None


class WhoisEntities(BaseModel):
    registrant: list[WhoisEntity] = Field(default_factory=list)
    administrative: list[WhoisEntity] = Field(default_factory=list)
    technical: list[WhoisEntity] = Field(default_factory=list)
    abuse: list[WhoisEntity] = Field(default_factory=list)
    billing: list[WhoisEntity] = Field(default_factory=list)
    registrar: list[WhoisEntity] = Field(default_factory=list)
    sponsor: list[WhoisEntity] = Field(default_factory=list)

    def get_registrant_name(self) -> str:
        for entity in self.registrant:
            name = entity.name.strip()
            if name and name.upper() not in ("REDACTED", "DATA REDACTED", "REDACTED FOR PRIVACY"):
                return name
        return ""

    def get_registrant_email(self) -> str:
        for entity in self.registrant:
            email = entity.email.strip()
            if email and "redacted" not in email.lower():
                return email
        return ""

    def get_registrar_name(self) -> str:
        for entity in self.registrar:
            if entity.name.strip():
                return entity.name.strip()
        return ""

    def get_abuse_email(self) -> str:
        for entity in self.abuse:
            if entity.email.strip():
                return entity.email.strip()
        return ""


class WhoisBaseResponse(BaseModel):
    lookup_type: WhoisLookupType
    query: str  # the original query value

    handle: str = ""
    parent_handle: str = ""
    name: str = ""
    whois_server: str = ""
    object_class: str = ""  # RDAP objectClassName e.g. "domain", "ip network", "autnum"

    terms_of_service_url: str = ""
    copyright_notice: str = ""

    description: list[str] = Field(default_factory=list)

    registration_date: datetime | None = None
    last_changed_date: datetime | None = None
    expiration_date: datetime | None = None

    rir: str = ""
    url: str = ""  # RDAP query URL

    entities: WhoisEntities = Field(default_factory=WhoisEntities)

    def _base_db_fields(self) -> dict[str, Any]:
        return {
            "query_value": self.query,
            "lookup_type": self.lookup_type.value,
            "handle": self.handle,
            "name": self.name,
            "whois_server": self.whois_server,
            "object_class": self.object_class,
            "rir": self.rir,
            "description": "\n".join(self.description),
            "registration_date": self.registration_date,
            "last_changed_date": self.last_changed_date,
            "expiration_date": self.expiration_date,
            "registrant_name": self.entities.get_registrant_name(),
            "registrant_email": self.entities.get_registrant_email(),
            "registrar_name": self.entities.get_registrar_name(),
            "abuse_email": self.entities.get_abuse_email(),
            "parsed_data": self.model_dump(mode="json"),
        }

class WhoisDomainResponse(WhoisBaseResponse):

    lookup_type: WhoisLookupType = WhoisLookupType.DOMAIN

    unicode_name: str = ""
    nameservers: list[str] = Field(default_factory=list)
    status: list[str] = Field(default_factory=list)
    dnssec: bool = False

    def to_db_fields(self) -> dict[str, Any]:
        fields = self._base_db_fields()
        fields.update(
            {
                "nameservers": self.nameservers,
                "domain_status": self.status,
                "dnssec": self.dnssec,
                # IP/ASN fields stay as defaults
                "country": "",
                "ip_version": None,
                "assignment_type": "",
                "network_cidr": "",
                "asn_range_start": None,
                "asn_range_end": None,
            }
        )
        return fields


class WhoisIPResponse(WhoisBaseResponse):
    # for both ip and cidr lookups
    lookup_type: WhoisLookupType = WhoisLookupType.IP

    country: str = ""
    ip_version: int | None = None
    assignment_type: str = ""
    network: str = ""  # string representation of IPv4Network/IPv6Network

    def to_db_fields(self) -> dict[str, Any]:
        fields = self._base_db_fields()
        fields.update(
            {
                "country": self.country,
                "ip_version": self.ip_version,
                "assignment_type": self.assignment_type,
                "network_cidr": self.network,
                "nameservers": None,
                "domain_status": None,
                "dnssec": None,
                "asn_range_start": None,
                "asn_range_end": None,
            }
        )
        return fields

class WhoisASNResponse(WhoisBaseResponse):

    lookup_type: WhoisLookupType = WhoisLookupType.ASN

    asn_range_start: int | None = None
    asn_range_end: int | None = None

    def to_db_fields(self) -> dict[str, Any]:
        fields = self._base_db_fields()
        fields.update(
            {
                "asn_range_start": self.asn_range_start,
                "asn_range_end": self.asn_range_end,
                "nameservers": None,
                "domain_status": None,
                "dnssec": None,
                "country": "",
                "ip_version": None,
                "assignment_type": "",
                "network_cidr": "",
            }
        )
        return fields

WhoisResponse = WhoisDomainResponse | WhoisIPResponse | WhoisASNResponse
