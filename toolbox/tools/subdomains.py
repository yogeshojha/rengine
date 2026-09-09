"""Passive subdomain enumeration over the same providers the scan stage uses."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from pydantic import Field, field_validator

from shared.definitions.toolbox import (
    MAX_INPUT_LENGTH,
    InputKind,
    Tone,
    ToolExecution,
    ToolGroup,
)
from shared.enums.api_key import APIProvider
from shared.utils.validation import normalize_domain, validate_domain
from stages.subdomain.parser import merge_and_filter
from stages.subdomain.providers.assetfinder import AssetfinderProvider
from stages.subdomain.providers.base import ProviderContext, ProviderResult
from stages.subdomain.providers.crtname import CrtNameProvider
from stages.subdomain.providers.subfinder import SubfinderProvider
from toolbox import estate
from toolbox.base import (
    Tool,
    ToolContext,
    ToolError,
    ToolInput,
    ToolOutcome,
    cell,
    glyph,
    hero,
    lookup,
    mark,
    meter,
    metric,
    note,
    table,
)
from toolbox.pivot import target_pivot_sync

SOURCES = {
    "subfinder": SubfinderProvider,
    "assetfinder": AssetfinderProvider,
    "certificates": CrtNameProvider,
}

SOURCE_LABELS = {
    "subfinder": "subfinder",
    "assetfinder": "assetfinder",
    "certificates": "certificate transparency",
}

DEFAULT_SOURCES = ["subfinder", "assetfinder"]
PREFETCH_KEYS = (APIProvider.SECURITYTRAILS, APIProvider.CHAOS)
TOOL_TIMEOUT = 120
MAX_LISTED = 500


class Input(ToolInput):
    domain: str = Field(
        ...,
        min_length=1,
        max_length=MAX_INPUT_LENGTH,
        title="Domain",
        description="Registrable domain to enumerate",
    )
    sources: list[str] = Field(
        default=list(DEFAULT_SOURCES),
        title="Sources",
        description="Passive sources to query",
        json_schema_extra={"options": list(SOURCES), "option_labels": SOURCE_LABELS},
    )

    @field_validator("domain")
    @classmethod
    def _domain(cls, value: str) -> str:
        cleaned = normalize_domain(value)
        if not validate_domain(cleaned):
            msg = f"{value} is not a domain name."
            raise ValueError(msg)
        return cleaned

    @field_validator("sources")
    @classmethod
    def _sources(cls, value: list[str]) -> list[str]:
        chosen = [v for v in value if v in SOURCES]
        if not chosen:
            msg = "Select at least one source."
            raise ValueError(msg)
        return chosen


class SubdomainFinder(Tool):
    name = "subdomains"
    title = "Subdomain finder"
    description = "Hostnames for a domain from passive sources."
    group = ToolGroup.DISCOVERY.value
    icon = "git-fork"
    execution = ToolExecution.QUEUED.value
    auto = False
    accepts = frozenset({InputKind.DOMAIN.value, InputKind.URL.value})
    order = 40
    value_field = "domain"
    placeholder = "example.com"
    examples = ("example.com",)
    Input = Input

    def run(self, ctx: ToolContext, args: Input) -> ToolOutcome:
        pctx = ProviderContext(
            domain=args.domain,
            timeout=TOOL_TIMEOUT,
            threads=20,
            proxy_url=None,
            api_keys=_api_keys(ctx),
        )
        with ThreadPoolExecutor(max_workers=len(args.sources)) as pool:
            results = list(pool.map(lambda key: SOURCES[key](pctx).run(), args.sources))

        merged = merge_and_filter(results, args.domain, [])
        names = sorted(merged)
        if not names and all(r.error for r in results):
            raise ToolError(next(r.error for r in results if r.error))

        known = estate.known_hosts_sync(ctx.session, ctx.project_id, names)
        new = [n for n in names if n not in known]
        ran = sum(1 for r in results if not r.error and not r.skipped)

        blocks = [
            hero(
                args.domain,
                sub=f"{len(names)} hostname{'s' if len(names) != 1 else ''} from "
                f"{ran} source{'s' if ran != 1 else ''}",
                identity=glyph("git-fork"),
                metric=metric(
                    len(new),
                    "Not in inventory",
                    tone=Tone.INFO.value if new else Tone.MUTED.value,
                ),
                meter=meter(
                    len(known) / len(names) if names else 0.0,
                    caption=f"{len(known)} of {len(names)} already known",
                    tone=Tone.SUCCESS.value,
                )
                if names
                else None,
                marks=[
                    mark(
                        SOURCE_LABELS.get(key, key),
                        tone=_source_tone(result),
                        note=_source_note(result),
                    )
                    for key, result in zip(args.sources, results, strict=True)
                ],
            ),
            table(
                ["Host", "Found by", "Inventory"],
                [
                    [
                        cell(name, mono=True, lookup=lookup(name)),
                        cell(
                            ", ".join(
                                sorted(SOURCE_LABELS.get(s, s) for s in merged[name])
                            ),
                            tone=Tone.MUTED.value,
                        ),
                        cell("known", tone=Tone.MUTED.value)
                        if name in known
                        else cell("new", tone=Tone.INFO.value),
                    ]
                    for name in names[:MAX_LISTED]
                ],
                title="Hosts",
                empty="No hostnames returned",
                total=len(names),
            ),
        ]
        if len(names) > MAX_LISTED:
            blocks.append(
                note(f"First {MAX_LISTED} of {len(names)} shown.", tone=Tone.INFO.value)
            )

        return ToolOutcome(
            summary=f"{len(names)} host{'s' if len(names) != 1 else ''} · "
            f"{len(new)} not in inventory",
            blocks=blocks,
            caveats=[
                "Passive sources only. Bruteforce, permutations and DNS resolution "
                "require a scan."
            ],
            pivot=target_pivot_sync(ctx, args.domain),
            raw={"domain": args.domain, "hosts": names, "new": new},
        )


def _source_tone(result: ProviderResult) -> str:
    if result.error:
        return Tone.CRITICAL.value
    if result.skipped:
        return Tone.MUTED.value
    return Tone.SUCCESS.value if result.subdomains else Tone.MUTED.value


def _source_note(result: ProviderResult) -> str:
    if result.error:
        return result.error
    if result.skipped:
        return result.skip_reason or "skipped"
    return f"{len(result.subdomains)} in {result.duration_seconds:.0f}s"


def _api_keys(ctx: ToolContext) -> dict[str, str | None]:
    from shared.services.api_key.sync_api_key import SyncAPIKeyService  # noqa: PLC0415

    service = SyncAPIKeyService(ctx.session)
    return {p.value: service.get_key_for_provider(p) for p in PREFETCH_KEYS}
