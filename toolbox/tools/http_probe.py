"""One HTTP request through the same httpx path the scanner uses."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from shared.definitions.toolbox import (
    MAX_INPUT_LENGTH,
    BlockKind,
    InputKind,
    Tone,
    ToolExecution,
    ToolGroup,
)
from shared.utils.datetime import utc_now
from toolbox.base import (
    Tool,
    ToolContext,
    ToolError,
    ToolInput,
    ToolOutcome,
    code,
    fact,
    facts,
    hero,
    lookup,
    mark,
    metric,
    tag,
    tags,
)
from toolbox.base import tech as tech_identity
from toolbox.guard import hostname_of, require_public
from toolbox.pivot import target_pivot_sync
from tools.httpx.client import HttpxClient, HttpxError
from tools.httpx.parser import parse_httpx_record

PROBE_TIMEOUT = 15
CERT_WARNING_DAYS = 30
OK_STATUS = 400
REDIRECT_STATUS = 300


class Input(ToolInput):
    target: str = Field(
        ...,
        min_length=1,
        max_length=MAX_INPUT_LENGTH,
        title="Host or URL",
        description="example.com · https://example.com/login · 93.184.216.34",
    )
    follow_redirects: bool = Field(
        default=True,
        title="Follow redirects",
        description="Report the final response in the redirect chain",
    )


class HttpProbe(Tool):
    name = "http"
    title = "HTTP probe"
    description = "Status, title, server, technologies, certificate and CDN for a host."
    group = ToolGroup.DISCOVERY.value
    icon = "globe"
    execution = ToolExecution.QUEUED.value
    touches_target = True
    auto = False
    accepts = frozenset(
        {InputKind.DOMAIN.value, InputKind.URL.value, InputKind.IP.value}
    )
    order = 30
    value_field = "target"
    placeholder = "example.com or https://example.com/login"
    examples = ("example.com", "https://example.com/login")
    Input = Input

    def run(self, ctx: ToolContext, args: Input) -> ToolOutcome:
        require_public(args.target)
        try:
            client = HttpxClient(
                timeout=PROBE_TIMEOUT,
                threads=1,
                follow_redirects=args.follow_redirects,
            )
            with client.stream_probe([args.target]) as stream:
                records = list(stream.records)
        except HttpxError as exc:
            raise ToolError(str(exc)) from exc

        if not records:
            msg = f"{args.target} did not answer an HTTP request."
            raise ToolError(msg)

        row = parse_httpx_record(records[0])
        status = row.get("status_code")
        tech = row.get("tech") or []

        blocks = [
            _hero(row, status, tech),
            facts(
                fact("URL", row.get("final_url") or row.get("url"), mono=True),
                fact("Server", row.get("webserver")),
                fact("Content type", row.get("content_type")),
                fact("Size", _bytes(row.get("content_length"))),
                fact("Response time", _seconds(row.get("response_time"))),
                fact("Redirected to", row.get("location"), mono=True),
                title="Response",
            ),
            tags(
                [tag(name, identity=tech_identity(name)) for name in tech],
                title="Technologies",
                empty="No technologies detected",
            ),
            facts(*_tls(row), title="Certificate", empty="Response was not over TLS"),
            facts(
                fact(
                    "Address",
                    row.get("ip"),
                    mono=True,
                    lookup=lookup(row.get("ip") or ""),
                ),
                fact(
                    "CNAME",
                    row.get("cname"),
                    mono=True,
                    lookup=lookup(row.get("cname") or "", tool="dns"),
                ),
                fact(
                    "Network",
                    f"AS{row['asn']} {row.get('asn_org') or ''}".strip()
                    if row.get("asn")
                    else "",
                    lookup=lookup(f"AS{row['asn']}") if row.get("asn") else None,
                ),
                title="Network",
            ),
            code(
                row.get("raw_response_header") or "",
                lang="http",
                title="Response headers",
            ),
        ]

        return ToolOutcome(
            summary=_summary(status, row.get("webserver"), len(tech)),
            blocks=[b for b in blocks if b.kind != BlockKind.CODE.value or b.text],
            pivot=target_pivot_sync(ctx, hostname_of(args.target)),
            raw=_raw(row),
        )


def _hero(row: dict, status: int | None, tech: list) -> object:
    not_after = row.get("tls_not_after")
    expired = row.get("tls_expired") or (
        isinstance(not_after, datetime) and not_after < utc_now()
    )
    lead = row.get("webserver") or (tech[0] if tech else "")
    return hero(
        row.get("host") or row.get("url") or "",
        sub=row.get("title") or row.get("final_url") or row.get("url"),
        identity=tech_identity(lead) if lead else None,
        metric=metric(status, "Status", tone=_status_tone(status)),
        marks=[
            mark(
                "TLS",
                tone=Tone.CRITICAL.value
                if expired
                else (Tone.SUCCESS.value if not_after else Tone.MUTED.value),
                note="expired"
                if expired
                else ((row.get("tls_version") or "").upper() or "none"),
            ),
            mark(
                "CDN",
                tone=Tone.INFO.value if row.get("is_cdn") else Tone.MUTED.value,
                note=_edge(row),
            ),
            mark(
                "HTTP/2",
                tone=Tone.NEUTRAL.value
                if row.get("supports_http2")
                else Tone.MUTED.value,
                note="supported" if row.get("supports_http2") else "not offered",
            ),
            mark(
                "Technologies",
                tone=Tone.NEUTRAL.value if tech else Tone.MUTED.value,
                note=str(len(tech)) if tech else "none detected",
            ),
        ],
        tone=_status_tone(status),
    )


def _summary(status: int | None, server: str | None, tech: int) -> str:
    parts = [str(status) if status else "No status"]
    if server:
        parts.append(server)
    if tech:
        parts.append(f"{tech} technolog{'ies' if tech != 1 else 'y'}")
    return " · ".join(parts)


def _status_tone(status: int | None) -> str:
    if status is None:
        return Tone.MUTED.value
    if status < REDIRECT_STATUS:
        return Tone.SUCCESS.value
    if status < OK_STATUS:
        return Tone.INFO.value
    return Tone.WARNING.value


def _bytes(value: int | None) -> str:
    if not value:
        return ""
    return f"{value:,} bytes"


def _seconds(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value * 1000:.0f} ms" if value < 1 else f"{value:.2f} s"


def _edge(row: dict) -> str:
    if not row.get("is_cdn"):
        return "none"
    kind = row.get("cdn_type") or "cdn"
    return f"{row.get('cdn_name') or kind} ({kind})"


def _tls(row: dict) -> list:
    not_after = row.get("tls_not_after")
    tone, note = Tone.NEUTRAL.value, None
    if isinstance(not_after, datetime):
        days = (not_after - utc_now()).days
        if days < 0:
            tone, note = Tone.CRITICAL.value, f"expired {abs(days)} days ago"
        elif days <= CERT_WARNING_DAYS:
            tone, note = Tone.WARNING.value, f"in {days} days"
        else:
            note = f"in {days} days"
    return [
        fact("Issuer", row.get("tls_issuer_org") or row.get("tls_issuer_cn")),
        fact("Subject", row.get("tls_subject_cn"), mono=True),
        fact("Protocol", (row.get("tls_version") or "").upper()),
        fact("Cipher", row.get("tls_cipher"), mono=True),
        fact(
            "Expires",
            not_after.date().isoformat() if isinstance(not_after, datetime) else "",
            tone=tone,
            note=note,
        ),
        fact(
            "Self-signed",
            "yes" if row.get("tls_self_signed") else "",
            tone=Tone.CRITICAL.value,
        ),
        fact("Subject alternative names", ", ".join(row.get("tls_sans") or [])),
    ]


_RAW_DROP = ("response_body", "raw_request", "raw_response_header", "body_preview")


def _raw(row: dict) -> dict:
    return {
        k: v for k, v in row.items() if k not in _RAW_DROP and v not in (None, "", [])
    }
