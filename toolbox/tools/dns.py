"""All DNS record types for a domain, in one dnsx invocation."""

from __future__ import annotations

from pydantic import Field, field_validator

from shared.definitions.toolbox import (
    MAX_INPUT_LENGTH,
    InputKind,
    Tone,
    ToolExecution,
    ToolGroup,
)
from shared.enums.dns import DnsRecordType
from shared.utils.validation import normalize_domain, validate_domain
from toolbox.base import (
    Tool,
    ToolContext,
    ToolError,
    ToolInput,
    ToolOutcome,
    cell,
    hero,
    lookup,
    mark,
    metric,
    nameserver,
    table,
)
from toolbox.pivot import target_pivot_sync
from tools.dnsx.service import DnsxService, DnsxServiceError

RECORD_ORDER = (
    DnsRecordType.A,
    DnsRecordType.AAAA,
    DnsRecordType.CNAME,
    DnsRecordType.NS,
    DnsRecordType.MX,
    DnsRecordType.TXT,
    DnsRecordType.SOA,
    DnsRecordType.SRV,
    DnsRecordType.CAA,
)

_TXT_PURPOSE = (
    ("v=spf1", "SPF sender policy"),
    ("v=dmarc1", "DMARC policy"),
    ("v=dkim1", "DKIM key"),
    ("-site-verification", "Domain verification"),
    ("-domain-verification", "Domain verification"),
)


class Input(ToolInput):
    domain: str = Field(
        ...,
        min_length=1,
        max_length=MAX_INPUT_LENGTH,
        title="Domain",
        description="Domain name to resolve",
    )

    @field_validator("domain")
    @classmethod
    def _domain(cls, value: str) -> str:
        cleaned = normalize_domain(value)
        if not validate_domain(cleaned):
            msg = f"{value} is not a domain name."
            raise ValueError(msg)
        return cleaned


class DnsLookup(Tool):
    name = "dns"
    title = "DNS records"
    description = (
        "Address, mail, nameserver, text and CAA records published for a domain."
    )
    group = ToolGroup.LOOKUP.value
    icon = "list-tree"
    execution = ToolExecution.QUEUED.value
    accepts = frozenset({InputKind.DOMAIN.value, InputKind.URL.value})
    order = 20
    value_field = "domain"
    placeholder = "example.com"
    examples = ("example.com",)
    Input = Input

    def run(self, ctx: ToolContext, args: Input) -> ToolOutcome:
        try:
            recon = DnsxService().do_recon(args.domain)
        except DnsxServiceError as exc:
            raise ToolError(str(exc)) from exc

        rows = _rows(recon)
        status = (recon.status_code or "").upper()
        addresses = len(recon.a) + len(recon.aaaa)
        answered = status in ("", "NOERROR")

        blocks = [
            hero(
                args.domain,
                sub=f"{len(rows)} record{'s' if len(rows) != 1 else ''}"
                + ("" if answered else f" · {status}"),
                identity=nameserver(recon.ns[0]) if recon.ns else None,
                metric=metric(addresses, "Addresses"),
                marks=[
                    mark(
                        "Nameservers",
                        note=str(len(recon.ns)) if recon.ns else "none",
                        tone=Tone.NEUTRAL.value if recon.ns else Tone.WARNING.value,
                    ),
                    mark(
                        "Mail",
                        note=str(len(recon.mx)) if recon.mx else "none",
                        tone=Tone.NEUTRAL.value if recon.mx else Tone.MUTED.value,
                    ),
                    mark(
                        "CDN",
                        tone=Tone.INFO.value if recon.cdn else Tone.MUTED.value,
                        note=(recon.cdn_name or "yes") if recon.cdn else "none",
                    ),
                    mark(
                        "Zone transfer",
                        tone=Tone.CRITICAL.value if recon.axfr else Tone.MUTED.value,
                        note="open" if recon.axfr else "refused",
                    ),
                ],
                tone=Tone.NEUTRAL.value if answered else Tone.WARNING.value,
            ),
            table(
                ["Type", "Value"],
                rows,
                title="Records",
                empty="No records returned",
                total=len(rows),
            ),
        ]

        summary = (
            f"{len(rows)} records · {addresses} address{'es' if addresses != 1 else ''}"
            if rows
            else f"No records returned ({status or 'no answer'})"
        )
        return ToolOutcome(
            summary=summary,
            blocks=blocks,
            pivot=target_pivot_sync(ctx, args.domain),
            raw=recon.model_dump(mode="json"),
        )


def _txt_note(value: str) -> str | None:
    lowered = value.lower()
    for token, label in _TXT_PURPOSE:
        if token in lowered:
            return label
    return None


def _rows(recon) -> list[list]:
    rows: list[list] = []

    def add(kind: DnsRecordType, value: str, hint: str | None = None, **kw) -> None:
        rows.append(
            [
                cell(kind.value, tone=Tone.MUTED.value),
                cell(value, mono=True, note=hint, **kw),
            ]
        )

    for value in recon.a:
        add(DnsRecordType.A, value, lookup=lookup(value))
    for value in recon.aaaa:
        add(DnsRecordType.AAAA, value, lookup=lookup(value))
    for value in recon.cname:
        add(DnsRecordType.CNAME, value, lookup=lookup(value, tool="dns"))
    for value in recon.ns:
        add(
            DnsRecordType.NS,
            value,
            identity=nameserver(value),
            lookup=lookup(value, tool="dns"),
        )
    for entry in recon.mx:
        add(
            DnsRecordType.MX,
            entry.host,
            f"priority {entry.priority}",
            lookup=lookup(entry.host, tool="dns"),
        )
    for value in recon.txt:
        add(DnsRecordType.TXT, value, _txt_note(value))
    for entry in recon.soa:
        add(DnsRecordType.SOA, entry.ns, f"{entry.mailbox} · serial {entry.serial}")
    for entry in recon.srv:
        add(DnsRecordType.SRV, f"{entry.target}:{entry.port}", f"weight {entry.weight}")
    for entry in recon.caa:
        add(DnsRecordType.CAA, entry.value, entry.tag)
    return rows
