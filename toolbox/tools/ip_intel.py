"""Address facts from the offline range tables, plus its recorded scan history."""

from __future__ import annotations

import asyncio
import ipaddress
import socket

from pydantic import Field, field_validator
from sqlalchemy import func, select

from shared.definitions.surface import SurfaceDimension
from shared.definitions.toolbox import (
    MAX_INPUT_LENGTH,
    Pivot,
    Tone,
    ToolExecution,
    ToolGroup,
)
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.services.ip_asn import ADDRESS_LOOKUP_SQL
from toolbox.base import (
    Tool,
    ToolContext,
    ToolInput,
    ToolOutcome,
    fact,
    facts,
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
    placeholder = "8.8.8.8"
    examples = ("8.8.8.8", "1.1.1.1")
    Input = Input

    async def run(self, ctx: ToolContext, args: Input) -> ToolOutcome:
        address = ipaddress.ip_address(args.ip)
        row = (await ctx.session.execute(ADDRESS_LOOKUP_SQL, {"ip": args.ip})).first()
        asn, as_name, country = row if row else (None, None, None)
        ptr = await _reverse(args.ip)
        seen = await _seen(ctx, args.ip)

        blocks = [
            facts(
                fact("Address", args.ip, mono=True),
                fact("Version", f"IPv{address.version}"),
                fact("Network", f"AS{asn}" if asn else "", mono=True),
                fact("Operator", as_name),
                fact("Country", country),
                fact(
                    "Routing",
                    "public" if address.is_global else "not publicly routable",
                    tone=Tone.NEUTRAL.value
                    if address.is_global
                    else Tone.WARNING.value,
                ),
                title="Address",
            ),
            tags(
                [tag(name, icon="server") for name in ptr],
                title="Reverse DNS",
                empty="No PTR record",
            ),
            facts(
                *_seen_facts(seen),
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
            if seen["rows"]
            else None,
            raw={
                "ip": args.ip,
                "asn": asn,
                "as_name": as_name,
                "country": country,
                "ptr": ptr,
                **seen,
            },
        )


async def _reverse(ip: str) -> list[str]:
    def lookup() -> list[str]:
        try:
            name, aliases, _ = socket.gethostbyaddr(ip)
        except OSError:
            return []
        return [name, *aliases] if name else list(aliases)

    try:
        return await asyncio.wait_for(asyncio.to_thread(lookup), PTR_TIMEOUT)
    except TimeoutError:
        return []


async def _seen(ctx: ToolContext, ip: str) -> dict:
    if ctx.project_id is None:
        return {"rows": 0, "targets": 0, "scans": 0, "ports": 0, "last_seen": None}
    scoped = IpAddress.project_id == ctx.project_id
    row = (
        await ctx.session.execute(
            select(
                func.count(IpAddress.id),
                func.count(func.distinct(IpAddress.target_id)),
                func.count(func.distinct(IpAddress.scan_id)),
                func.max(IpAddress.discovered_at),
            ).where(scoped, IpAddress.ip == ip)
        )
    ).first()
    ports = await ctx.session.scalar(
        select(func.count(func.distinct(Port.number))).where(
            Port.project_id == ctx.project_id, Port.ip == ip
        )
    )
    return {
        "rows": int(row[0] or 0),
        "targets": int(row[1] or 0),
        "scans": int(row[2] or 0),
        "ports": int(ports or 0),
        "last_seen": row[3].isoformat() if row[3] else None,
    }


def _seen_facts(seen: dict) -> list:
    if not seen["rows"]:
        return []
    return [
        fact("Targets", seen["targets"]),
        fact("Scans", seen["scans"]),
        fact("Open ports", seen["ports"] or ""),
        fact("Last seen", (seen["last_seen"] or "")[:10]),
    ]
