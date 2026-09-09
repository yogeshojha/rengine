"""Every DNS record a name publishes, in one query."""

from __future__ import annotations

from pydantic import Field, field_validator

from shared.definitions.toolbox import MAX_INPUT_LENGTH, Tone, ToolExecution, ToolGroup
from shared.enums.dns import DnsRecordType
from shared.utils.validation import normalize_domain, validate_domain
from toolbox.base import (
    Tool,
    ToolContext,
    ToolError,
    ToolInput,
    ToolOutcome,
    cell,
    fact,
    facts,
    note,
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
        description="The name to resolve.",
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
        "Every record a name publishes: addresses, mail, nameservers, text, CAA."
    )
    group = ToolGroup.LOOKUP.value
    icon = "list-tree"
    execution = ToolExecution.QUEUED.value
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
        blocks = [
            facts(
                fact("Answer", status, mono=True, tone=Tone.WARNING.value)
                if status and status != "NOERROR"
                else None,
                fact(
                    "Behind a CDN",
                    (recon.cdn_name or "yes") if recon.cdn else "",
                    tone=Tone.INFO.value,
                ),
                fact("Zone transfer", ", ".join(recon.axfr), tone=Tone.CRITICAL.value)
                if recon.axfr
                else None,
                title="Resolution",
            ),
            table(
                ["Type", "Value"],
                rows,
                title="Records",
                empty="The name resolves, but publishes no records we asked for.",
                total=len(rows),
            ),
        ]
        if status and status != "NOERROR":
            blocks.insert(
                0, note(f"The resolver answered {status}.", tone=Tone.WARNING.value)
            )

        addresses = len(recon.a) + len(recon.aaaa)
        summary = (
            f"{len(rows)} records · {addresses} address{'es' if addresses != 1 else ''}"
            if rows
            else f"No records ({status or 'no answer'})"
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

    def add(kind: DnsRecordType, value: str, hint: str | None = None) -> None:
        rows.append(
            [cell(kind.value, tone=Tone.MUTED.value), cell(value, mono=True, note=hint)]
        )

    for value in recon.a:
        add(DnsRecordType.A, value)
    for value in recon.aaaa:
        add(DnsRecordType.AAAA, value)
    for value in recon.cname:
        add(DnsRecordType.CNAME, value)
    for value in recon.ns:
        add(DnsRecordType.NS, value)
    for entry in recon.mx:
        add(DnsRecordType.MX, entry.host, f"priority {entry.priority}")
    for value in recon.txt:
        add(DnsRecordType.TXT, value, _txt_note(value))
    for entry in recon.soa:
        add(DnsRecordType.SOA, entry.ns, f"{entry.mailbox} · serial {entry.serial}")
    for entry in recon.srv:
        add(DnsRecordType.SRV, f"{entry.target}:{entry.port}", f"weight {entry.weight}")
    for entry in recon.caa:
        add(DnsRecordType.CAA, entry.value, entry.tag)
    return rows
