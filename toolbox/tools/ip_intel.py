"""Address facts from the offline range tables, plus its recorded scan history."""

from __future__ import annotations

import asyncio
import ipaddress
import socket

from pydantic import Field, field_validator

from shared.definitions.surface import SurfaceDimension
from shared.definitions.toolbox import (
    MAX_INPUT_LENGTH,
    InputKind,
    Pivot,
    Tone,
    ToolExecution,
    ToolGroup,
)
from shared.services.ip_asn import ADDRESS_LOOKUP_SQL
from toolbox import estate
from toolbox.base import (
    Tool,
    ToolContext,
    ToolInput,
    ToolOutcome,
    fact,
    facts,
    flag,
    glyph,
    hero,
    lookup,
    mark,
    metric,
    note,
    tag,
    tags,
)

PTR_TIMEOUT = 4


class Input(ToolInput):
    ip: str = Field(
        ...,
        min_length=1,
        max_length=MAX_INPUT_LENGTH,
        title="IP address",
        description="8.8.8.8 · 2606:4700::1111",
    )

    @field_validator("ip")
    @classmethod
    def _ip(cls, value: str) -> str:
        try:
            return str(ipaddress.ip_address(value.strip()))
        except ValueError as exc:
            msg = f"{value} is not an IP address."
            raise ValueError(msg) from exc


class IpIntel(Tool):
    name = "ip"
    title = "IP address"
    description = "Network, operator, country and reverse DNS for an address, with its scan history."
    group = ToolGroup.LOOKUP.value
    icon = "network"
    execution = ToolExecution.INLINE.value
    accepts = frozenset({InputKind.IP.value})
    order = 10
    value_field = "ip"
    placeholder = "8.8.8.8"
    examples = ("8.8.8.8", "1.1.1.1")
    Input = Input

    async def run(self, ctx: ToolContext, args: Input) -> ToolOutcome:
        address = ipaddress.ip_address(args.ip)
        row = (await ctx.session.execute(ADDRESS_LOOKUP_SQL, {"ip": args.ip})).first()
        asn, as_name, country = row if row else (None, None, None)
        ptr = await _reverse(args.ip)
        seen = await estate.address(ctx.session, ctx.project_id, args.ip)
        net = await estate.network(ctx.session, ctx.project_id, asn)

        sub = ptr[0] if ptr else f"IPv{address.version} address"
        blocks = [
            hero(
                args.ip,
                sub=sub,
                identity=flag(country) if country else glyph("network"),
                metric=metric(seen.ports or "", "Open ports recorded")
                or metric(
                    net.hosts or "", "Hosts on this network", tone=Tone.INFO.value
                )
                or metric(f"AS{asn}" if asn else "", "Network"),
                marks=[
                    mark(
                        "Routing",
                        tone=Tone.NEUTRAL.value
                        if address.is_global
                        else Tone.WARNING.value,
                        note="public" if address.is_global else "not publicly routable",
                    ),
                    mark(
                        "In this project",
                        tone=Tone.INFO.value if seen.rows else Tone.MUTED.value,
                        note=f"{seen.targets} target{'s' if seen.targets != 1 else ''}"
                        if seen.rows
                        else "not recorded",
                    ),
                ],
            ),
            facts(
                fact(
                    "Network",
                    f"AS{asn}" if asn else "",
                    mono=True,
                    lookup=lookup(f"AS{asn}") if asn else None,
                ),
                fact("Operator", as_name),
                fact(
                    "Country",
                    country,
                    identity=flag(country) if country else None,
                ),
                title="Network",
            ),
            tags(
                [
                    tag(name, identity=glyph("server"), lookup=lookup(name, tool="dns"))
                    for name in ptr
                ],
                title="Reverse DNS",
                empty="No PTR record",
            ),
            facts(
                fact("Targets", seen.targets),
                fact("Scans", seen.scans),
                fact("Open ports", seen.ports or ""),
                fact("Last seen", (seen.last_seen or "")[:10]),
                fact(
                    "On this network",
                    f"{net.hosts} host{'s' if net.hosts != 1 else ''} across "
                    f"{net.addresses} address{'es' if net.addresses != 1 else ''}"
                    if net.addresses
                    else "",
                    tone=Tone.INFO.value,
                ),
                title="Scan history",
                empty="Not recorded by any scan in this project",
            ),
        ]
        if asn is None and country is None:
            blocks.append(
                note(
                    "IP range feeds have not been loaded on this instance.",
                    tone=Tone.WARNING.value,
                )
            )

        summary = (
            " · ".join(
                p
                for p in (
                    f"AS{asn} {as_name}" if asn else None,
                    country,
                    ptr[0] if ptr else None,
                )
                if p
            )
            or f"IPv{address.version} address"
        )

        return ToolOutcome(
            summary=summary,
            blocks=blocks,
            pivot=Pivot(
                label="Open in IP addresses",
                dimension=SurfaceDimension.IPS.value,
                query=f'ip:"{args.ip}"',
            )
            if seen.rows
            else None,
            raw={
                "ip": args.ip,
                "asn": asn,
                "as_name": as_name,
                "country": country,
                "ptr": ptr,
                "targets": seen.targets,
                "scans": seen.scans,
                "ports": seen.ports,
            },
        )


async def _reverse(ip: str) -> list[str]:
    def lookup_ptr() -> list[str]:
        try:
            name, aliases, _ = socket.gethostbyaddr(ip)
        except OSError:
            return []
        return [name, *aliases] if name else list(aliases)

    try:
        return await asyncio.wait_for(asyncio.to_thread(lookup_ptr), PTR_TIMEOUT)
    except TimeoutError:
        return []
