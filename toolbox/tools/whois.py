"""RDAP registration records for a domain, address block or autonomous system."""

from __future__ import annotations

import ipaddress
from datetime import datetime

from pydantic import Field

from shared.definitions.toolbox import (
    MAX_INPUT_LENGTH,
    Tone,
    ToolExecution,
    ToolGroup,
)
from shared.enums.whois import WhoisLookupType
from shared.utils.datetime import utc_now
from shared.utils.privacy import is_redacted_name
from toolbox import estate
from toolbox.base import (
    Tool,
    ToolContext,
    ToolError,
    ToolInput,
    ToolOutcome,
    fact,
    facts,
    flag,
    glyph,
    hero,
    lookup,
    mark,
    meter,
    metric,
    tag,
    tags,
    tech,
)
from toolbox.pivot import target_pivot
from tools.whois.models import WhoisEntity
from tools.whois.service import WhoisError as WhoisServiceError
from tools.whois.service import WhoisService

EXPIRY_CRITICAL_DAYS = 30
EXPIRY_WARNING_DAYS = 90
EXPIRY_NOTE_DAYS = 365
EXPIRY_WINDOW_DAYS = 365
DAYS_PER_YEAR = 365.25

_LOCK_TOKENS = ("transferprohibited", "deleteprohibited")


class Input(ToolInput):
    query: str = Field(
        ...,
        min_length=1,
        max_length=MAX_INPUT_LENGTH,
        title="Domain, address, block or AS",
        description="example.com · 8.8.8.8 · 1.1.1.0/24 · AS13335",
    )


class WhoisLookup(Tool):
    name = "whois"
    title = "WHOIS"
    description = (
        "Registration and allocation records for a domain, address block or "
        "autonomous system."
    )
    group = ToolGroup.LOOKUP.value
    icon = "scroll-text"
    execution = ToolExecution.INLINE.value
    order = 10
    value_field = "query"
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
        if response.lookup_type == WhoisLookupType.DOMAIN:
            blocks, summary = await _domain(ctx, response)
        elif response.lookup_type == WhoisLookupType.ASN:
            blocks, summary = await _asn(ctx, response)
        else:
            blocks, summary = _network(response)

        caveats = []
        if result.cache_hit:
            caveats.append("Served from the stored record, not a fresh query.")

        return ToolOutcome(
            summary=summary,
            blocks=blocks,
            caveats=caveats,
            pivot=await target_pivot(ctx, response.query),
            raw=response.model_dump(mode="json"),
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


def _days_to(value: datetime | None) -> int | None:
    return None if value is None else (value - utc_now()).days


def _expiry_tone(days: int | None) -> tuple[str, str | None]:
    """A countdown is only attached within a year of expiry."""
    if days is None:
        return Tone.NEUTRAL.value, None
    if days < 0:
        return Tone.CRITICAL.value, f"expired {abs(days)} days ago"
    if days <= EXPIRY_CRITICAL_DAYS:
        return Tone.CRITICAL.value, f"in {days} days"
    if days <= EXPIRY_WARNING_DAYS:
        return Tone.WARNING.value, f"in {days} days"
    if days <= EXPIRY_NOTE_DAYS:
        return Tone.NEUTRAL.value, f"in {days} days"
    return Tone.NEUTRAL.value, None


def _age(value: datetime | None) -> str:
    if value is None:
        return ""
    years = (utc_now() - value).days / DAYS_PER_YEAR
    return f"{years:.0f} years old" if years >= 1 else "under a year old"


async def _domain(ctx: ToolContext, response) -> tuple[list, str]:
    registrar = _named(_first(response.entities.registrar))
    registrant = _first(response.entities.registrant)
    days = _days_to(response.expiration_date)
    expiry_tone, expiry_note = _expiry_tone(days)
    redacted = is_redacted_name(_named(registrant))
    flat = [s.lower().replace(" ", "").replace("client", "") for s in response.status]
    locked = [s for s in flat if s in _LOCK_TOKENS]
    siblings = await estate.registrant_domains(
        ctx.session, ctx.project_id, _named(registrant), response.query
    )

    sub = " · ".join(p for p in (registrar, _age(response.registration_date)) if p)
    head = hero(
        response.query,
        sub=sub or None,
        identity=tech(registrar) if registrar else None,
        metric=metric(
            ("Expired" if days < 0 else f"{days} days") if days is not None else "",
            "Until expiry",
            tone=expiry_tone,
        ),
        meter=meter(
            min(days, EXPIRY_WINDOW_DAYS) / EXPIRY_WINDOW_DAYS
            if days and days > 0
            else 0.0,
            caption=_date(response.expiration_date),
            tone=expiry_tone,
        )
        if days is not None
        else None,
        marks=[
            mark(
                "DNSSEC",
                tone=Tone.SUCCESS.value if response.dnssec else Tone.MUTED.value,
                note="signed" if response.dnssec else "unsigned",
            ),
            mark(
                "Transfer lock",
                tone=Tone.SUCCESS.value if locked else Tone.WARNING.value,
                note="on" if locked else "off",
            ),
            mark(
                "Registrant",
                tone=Tone.MUTED.value if redacted else Tone.NEUTRAL.value,
                note="privacy service"
                if redacted
                else _named(registrant) or "not published",
            ),
        ],
        tone=expiry_tone,
    )

    blocks = [
        head,
        facts(
            fact("Registered", _date(response.registration_date)),
            fact("Updated", _date(response.last_changed_date)),
            fact(
                "Expires",
                _date(response.expiration_date),
                tone=expiry_tone,
                note=expiry_note,
            ),
            title="Registration",
        ),
        facts(
            fact(
                "Organisation",
                _named(registrant),
                tone=Tone.MUTED.value if redacted else Tone.NEUTRAL.value,
                note="privacy service" if redacted else None,
            ),
            fact("Email", registrant.email if registrant else ""),
            fact(
                "Country",
                _country(registrant),
                identity=flag(_country(registrant)) if _country(registrant) else None,
            ),
            fact(
                "Also in this project",
                f"{siblings} other domain{'s' if siblings != 1 else ''} share this registrant"
                if siblings
                else "",
                tone=Tone.INFO.value,
            ),
            title="Registrant",
            empty="No registrant details published",
        ),
        tags(
            [
                tag(
                    ns.lower(),
                    identity=glyph("server"),
                    lookup=lookup(ns.lower(), "dns"),
                )
                for ns in response.nameservers
            ],
            title="Nameservers",
            empty="No nameservers in the record",
        ),
        tags(
            [tag(s) for s in response.status],
            title="EPP status",
            empty="No status codes in the record",
        ),
    ]
    summary = f"Registered with {registrar}" if registrar else "Registration record"
    if expiry_note and expiry_tone != Tone.NEUTRAL.value:
        summary = f"{summary} · expires {expiry_note}"
    return blocks, summary


def _size(network: str) -> str:
    try:
        return f"{ipaddress.ip_network(network, strict=False).num_addresses:,}"
    except ValueError:
        return ""


def _network(response) -> tuple[list, str]:
    abuse = _first(response.entities.abuse)
    holder = _first(response.entities.registrant) or _first(response.entities.technical)
    country = response.country or _country(holder)
    blocks = [
        hero(
            response.network or response.query,
            sub=" · ".join(
                p for p in (_named(holder) or response.name, response.rir.upper()) if p
            )
            or None,
            identity=flag(country) if country else None,
            metric=metric(_size(response.network), "Addresses"),
            marks=[
                mark("Assignment", note=response.assignment_type or "not stated"),
                mark("Country", note=country or "not stated"),
            ],
        ),
        facts(
            fact(
                "Network",
                response.network,
                mono=True,
                lookup=lookup(response.network, "whois"),
            ),
            fact("Name", response.name),
            fact("Handle", response.handle, mono=True),
            fact("Assignment", response.assignment_type),
            fact("Country", country, identity=flag(country) if country else None),
            fact("Registry", response.rir.upper() if response.rir else ""),
            fact("Registered", _date(response.registration_date)),
            fact("Updated", _date(response.last_changed_date)),
            title="Allocation",
        ),
        facts(
            fact("Holder", _named(holder)),
            fact("Abuse contact", abuse.email if abuse else ""),
            title="Contacts",
            empty="No contact published for this block",
        ),
    ]
    label = response.name or response.network or "Address block"
    return blocks, f"{label} · {response.rir.upper() or 'registry record'}"


async def _asn(ctx: ToolContext, response) -> tuple[list, str]:
    abuse = _first(response.entities.abuse)
    holder = _first(response.entities.registrant)
    country = _country(holder)
    span = ""
    if response.asn_range_start is not None:
        span = (
            f"AS{response.asn_range_start}"
            if response.asn_range_start == response.asn_range_end
            else f"AS{response.asn_range_start} to AS{response.asn_range_end}"
        )
    net = await estate.network(ctx.session, ctx.project_id, response.asn_range_start)

    blocks = [
        hero(
            response.name or response.query,
            sub=" · ".join(p for p in (span, response.rir.upper()) if p) or None,
            identity=flag(country) if country else glyph("route"),
            metric=metric(
                net.hosts or "", "Hosts in this project", tone=Tone.INFO.value
            )
            or metric(span or response.query, "Autonomous system"),
            marks=[
                mark("Operator", note=_named(holder) or "not published"),
                mark("Country", note=country or "not stated"),
                mark(
                    "Addresses here",
                    tone=Tone.INFO.value if net.addresses else Tone.MUTED.value,
                    note=str(net.addresses) if net.addresses else "none recorded",
                ),
            ],
        ),
        facts(
            fact("Name", response.name),
            fact("Range", span, mono=True),
            fact("Registry", response.rir.upper() if response.rir else ""),
            fact("Country", country, identity=flag(country) if country else None),
            fact("Registered", _date(response.registration_date)),
            fact("Updated", _date(response.last_changed_date)),
            title="Autonomous system",
        ),
        facts(
            fact("Operator", _named(holder)),
            fact("Abuse contact", abuse.email if abuse else ""),
            title="Contacts",
            empty="No contact published for this AS",
        ),
    ]
    return blocks, response.name or "Autonomous system record"
