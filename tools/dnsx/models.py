"""Pydantic models for dnsx JSON output.

Example dnsx JSONL record from dnsx -json -recon:
{
  "host": "example.com",
  "resolver": ["8.8.8.8:53"],
  "a": ["93.184.216.34"],
  "aaaa": ["2606:2800:220:1:248:1893:25c8:1946"],
  "cname": [],
  "mx": ["10 mail.example.com."],
  "ns": ["a.iana-servers.net.", "b.iana-servers.net."],
  "txt": ["v=spf1 -all"],
  "soa": [{"name":"example.com.","ns":"ns.icann.org.","mailbox":"noc.dns.icann.org.","serial":2024010101,"refresh":7200,"retry":3600,"expire":1209600,"minttl":3600}],
  "srv": [],
  "ptr": [],
  "caa": [{"flag":0,"tag":"issue","value":"letsencrypt.org"}],
  "axfr": null,
  "cdn": true,
  "cdn_name": "cloudflare",
  "status_code": "NOERROR",
  "timestamp": "2024-01-01T12:00:00.000000Z"
}
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DnsxSOAEntry(BaseModel):
    """SOA record parsed from dnsx JSON output."""

    name: str = ""
    ns: str = ""
    mailbox: str = ""
    serial: int = 0
    refresh: int = 0
    retry: int = 0
    expire: int = 0
    minttl: int = 0


class DnsxCAAEntry(BaseModel):
    flag: int = 0
    tag: str = ""
    value: str = ""


class DnsxMXEntry(BaseModel):
    priority: int = 0
    host: str = ""


class DnsxSRVEntry(BaseModel):
    priority: int = 0
    weight: int = 0
    port: int = 0
    target: str = ""


class DnsxRecord(BaseModel):
    host: str
    resolver: list[str] = Field(default_factory=list)

    a: list[str] = Field(default_factory=list)
    aaaa: list[str] = Field(default_factory=list)
    cname: list[str] = Field(default_factory=list)
    ns: list[str] = Field(default_factory=list)
    txt: list[str] = Field(default_factory=list)
    ptr: list[str] = Field(default_factory=list)

    mx_raw: list[str] = Field(default_factory=list, alias="mx")
    srv_raw: list[str] = Field(default_factory=list, alias="srv")

    soa_raw: list = Field(default_factory=list, alias="soa")

    caa_raw: list = Field(default_factory=list, alias="caa")

    axfr: list[str] | None = None

    # Probes
    cdn: bool = False
    cdn_name: str = ""

    status_code: str = ""
    timestamp: str = ""

    class Config:
        populate_by_name = True


class DnsxReconResponse(BaseModel):
    """Fully parsed DNS recon result for a single domain.

    This is the enriched/parsed version of DnsxRecord with structured
    MX, SRV, SOA, and CAA entries. Used by the service layer and stored
    in the database.
    """

    host: str

    # Core records
    a: list[str] = Field(default_factory=list)
    aaaa: list[str] = Field(default_factory=list)
    cname: list[str] = Field(default_factory=list)
    ns: list[str] = Field(default_factory=list)
    txt: list[str] = Field(default_factory=list)
    ptr: list[str] = Field(default_factory=list)

    # Structured records
    mx: list[DnsxMXEntry] = Field(default_factory=list)
    srv: list[DnsxSRVEntry] = Field(default_factory=list)
    soa: list[DnsxSOAEntry] = Field(default_factory=list)
    caa: list[DnsxCAAEntry] = Field(default_factory=list)

    # AXFR
    axfr: list[str] = Field(default_factory=list)

    # Probes
    cdn: bool = False
    cdn_name: str = ""

    # Status
    status_code: str = ""
    timestamp: str = ""

    def to_db_records(self) -> list[dict]:
        """Convert to list of flat dicts suitable for DnsRecord DB rows.

        Each DNS record type becomes one or more rows in the dns_records table.
        This enables queries like "find all targets with the same NS" easily.
        """
        records: list[dict] = []
        base = {"host": self.host}

        for ip in self.a:
            records.append({**base, "record_type": "A", "value": ip})

        for ip in self.aaaa:
            records.append({**base, "record_type": "AAAA", "value": ip})

        for cn in self.cname:
            records.append({**base, "record_type": "CNAME", "value": cn})

        for ns in self.ns:
            records.append({**base, "record_type": "NS", "value": ns})

        for txt in self.txt:
            records.append({**base, "record_type": "TXT", "value": txt})

        for ptr in self.ptr:
            records.append({**base, "record_type": "PTR", "value": ptr})

        for mx in self.mx:
            records.append(
                {
                    **base,
                    "record_type": "MX",
                    "value": mx.host,
                    "priority": mx.priority,
                }
            )

        for srv in self.srv:
            records.append(
                {
                    **base,
                    "record_type": "SRV",
                    "value": srv.target,
                    "priority": srv.priority,
                    "weight": srv.weight,
                    "port": srv.port,
                }
            )

        for soa in self.soa:
            records.append(
                {
                    **base,
                    "record_type": "SOA",
                    "value": soa.ns,
                    "soa_email": soa.mailbox,
                    "soa_serial": soa.serial,
                    "soa_refresh": soa.refresh,
                    "soa_retry": soa.retry,
                    "soa_expire": soa.expire,
                    "soa_minttl": soa.minttl,
                }
            )

        for caa in self.caa:
            records.append(
                {
                    **base,
                    "record_type": "CAA",
                    "value": caa.value,
                    "caa_tag": caa.tag,
                    "caa_flag": caa.flag,
                }
            )

        for axfr_entry in self.axfr:
            records.append({**base, "record_type": "AXFR", "value": axfr_entry})

        if self.cdn:
            records.append(
                {
                    **base,
                    "record_type": "CDN",
                    "value": self.cdn_name or "detected",
                }
            )

        return records
