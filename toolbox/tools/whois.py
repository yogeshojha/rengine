"""WHOIS/RDAP: who registered a name, who holds a block, who runs an AS."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from shared.definitions.toolbox import MAX_INPUT_LENGTH, Tone, ToolExecution, ToolGroup
from shared.enums.whois import WhoisLookupType
from shared.utils.datetime import utc_now
from shared.utils.privacy import is_redacted_name
from toolbox.base import (
    Tool,
    ToolContext,
    ToolError,
    ToolInput,
    ToolOutcome,
    fact,
    facts,
    tag,
    tags,
)
from toolbox.pivot import target_pivot
from tools.whois.models import WhoisEntity, WhoisResponse
from tools.whois.service import WhoisError as WhoisServiceError
from tools.whois.service import WhoisService

EXPIRY_CRITICAL_DAYS = 30
EXPIRY_WARNING_DAYS = 90
EXPIRY_NOTE_DAYS = 365

_LOCK_TOKENS = ("transferprohibited", "deleteprohibited")


class Input(ToolInput):
    query: str = Field(
        ...,
        min_length=1,
        max_length=MAX_INPUT_LENGTH,
        title="Domain, address, block or AS",
        description="example.com · 8.8.8.8 · 1.1.1.0/24 · AS13335",
    )


def _first(entities: list[WhoisEntity]) -> WhoisEntity | None:
    return entities[0] if entities else None


def _named(entity: WhoisEntity | None) -> str:
    if entity is None:
        return ""
    return entity.name or entity.handle or entity.email


def _country(entity: WhoisEntity | None) -> str:
    return entity.address.country if entity and entity.address else ""


def _date(value: datetime | None) -> str:
    return value.date().isoformat() if value else ""


def _expiry_tone(value: datetime | None) -> tuple[str, str | None]:
    """A date years out needs no countdown; only a near one is a fact worth stating."""
    if value is None:
        return Tone.NEUTRAL.value, None
    days = (value - utc_now()).days
    if days < 0:
        return Tone.CRITICAL.value, f"expired {abs(days)} days ago"
    if days <= EXPIRY_CRITICAL_DAYS:
        return Tone.CRITICAL.value, f"in {days} days"
    if days <= EXPIRY_WARNING_DAYS:
        return Tone.WARNING.value, f"in {days} days"
    if days <= EXPIRY_NOTE_DAYS:
        return Tone.NEUTRAL.value, f"in {days} days"
    return Tone.NEUTRAL.value, None


class WhoisLookup(Tool):
    name = "whois"
    title = "WHOIS"
    description = "Who registered a domain, who holds an address block, who runs an AS."
    group = ToolGroup.LOOKUP.value
    icon = "scroll-text"
    execution = ToolExecution.INLINE.value
    placeholder = "example.com, 8.8.8.8 or AS13335"
    examples = ("example.com", "8.8.8.8", "AS13335")
    Input = Input

    async def run(self, ctx: ToolContext, args: Input) -> ToolOutcome:
        service = WhoisService()
        try:
            service.ensure_ready()
            result = await service.lookup(
                query=args.query, store_in_db=True, session=ctx.session
            )
        except WhoisServiceError as exc:
            raise ToolError(str(exc)) from exc

        response = result.response
        blocks, summary = _render(response)

        caveats = []
        if result.cache_hit:
            caveats.append("Served from reNgine's stored record, not a fresh query.")

        return ToolOutcome(
            summary=summary,
            blocks=blocks,
            caveats=caveats,
            pivot=await target_pivot(ctx, response.query),
            raw=response.model_dump(mode="json"),
        )


def _render(response: WhoisResponse) -> tuple[list, str]:
    if response.lookup_type == WhoisLookupType.DOMAIN:
        return _domain(response)
    if response.lookup_type == WhoisLookupType.ASN:
        return _asn(response)
    return _network(response)


def _domain(response) -> tuple[list, str]:
    registrar = _named(_first(response.entities.registrar))
    registrant = _first(response.entities.registrant)
    expiry_tone, expiry_note = _expiry_tone(response.expiration_date)
    redacted = is_redacted_name(_named(registrant))
    flat = [s.lower().replace(" ", "").replace("client", "") for s in response.status]
    locked = [s for s in flat if s in _LOCK_TOKENS]

    blocks = [
        facts(
            fact("Registrar", registrar),
            fact("Registered", _date(response.registration_date)),
            fact("Updated", _date(response.last_changed_date)),
            fact(
                "Expires",
                _date(response.expiration_date),
                tone=expiry_tone,
                note=expiry_note,
            ),
            fact(
                "DNSSEC",
                "signed" if response.dnssec else "unsigned",
                tone=Tone.SUCCESS.value if response.dnssec else Tone.MUTED.value,
            ),
            fact(
                "Transfer lock",
                "on" if locked else "off",
                tone=Tone.SUCCESS.value if locked else Tone.WARNING.value,
            ),
            title="Registration",
        ),
        facts(
            fact(
                "Organisation",
                _named(registrant),
                tone=Tone.MUTED.value if redacted else Tone.NEUTRAL.value,
                note="a privacy service, not the owner" if redacted else None,
            ),
            fact("Email", registrant.email if registrant else ""),
            fact("Country", _country(registrant)),
            title="Registrant",
            empty="The registrar publishes no registrant details.",
        ),
        tags(
            [tag(ns, icon="server") for ns in response.nameservers],
            title="Nameservers",
            empty="No nameservers in the record.",
        ),
        tags(
            [tag(s) for s in response.status],
            title="EPP status",
            empty="No status codes in the record.",
        ),
    ]
    summary = (
        f"Registered with {registrar}" if registrar else "Registration record found"
    )
    if expiry_note and expiry_tone != Tone.NEUTRAL.value:
        summary = f"{summary} · expires {expiry_note}"
    return blocks, summary


def _network(response) -> tuple[list, str]:
    abuse = _first(response.entities.abuse)
    holder = _first(response.entities.registrant) or _first(response.entities.technical)
    blocks = [
        facts(
            fact("Network", response.network, mono=True),
            fact("Name", response.name),
            fact("Handle", response.handle, mono=True),
            fact("Assignment", response.assignment_type),
            fact("Country", response.country),
            fact("Registry", response.rir.upper() if response.rir else ""),
            fact("Registered", _date(response.registration_date)),
            fact("Updated", _date(response.last_changed_date)),
            title="Allocation",
        ),
        facts(
            fact("Holder", _named(holder)),
            fact("Abuse contact", abuse.email if abuse else ""),
            title="Contacts",
            empty="The registry publishes no contact for this block.",
        ),
    ]
    label = response.name or response.network or "Address block"
    return blocks, f"{label} · {response.rir.upper() or 'registry record'}"


def _asn(response) -> tuple[list, str]:
    abuse = _first(response.entities.abuse)
    span = ""
    if response.asn_range_start is not None:
        span = (
            f"AS{response.asn_range_start}"
            if response.asn_range_start == response.asn_range_end
            else f"AS{response.asn_range_start} to AS{response.asn_range_end}"
        )
    blocks = [
        facts(
            fact("Name", response.name),
            fact("Range", span, mono=True),
            fact("Registry", response.rir.upper() if response.rir else ""),
            fact("Country", _country(_first(response.entities.registrant))),
            fact("Registered", _date(response.registration_date)),
            fact("Updated", _date(response.last_changed_date)),
            title="Autonomous system",
        ),
        facts(
            fact("Operator", _named(_first(response.entities.registrant))),
            fact("Abuse contact", abuse.email if abuse else ""),
            title="Contacts",
            empty="The registry publishes no contact for this AS.",
        ),
    ]
    return blocks, response.name or "Autonomous system record found"
