"""Passive subdomain enumeration over the same providers the scan stage uses."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from pydantic import Field, field_validator

from shared.definitions.toolbox import MAX_INPUT_LENGTH, Tone, ToolExecution, ToolGroup
from shared.enums.api_key import APIProvider
from shared.utils.validation import normalize_domain, validate_domain
from stages.subdomain.parser import merge_and_filter
from stages.subdomain.providers.assetfinder import AssetfinderProvider
from stages.subdomain.providers.base import ProviderContext, ProviderResult
from stages.subdomain.providers.crtname import CrtNameProvider
from stages.subdomain.providers.subfinder import SubfinderProvider
from toolbox.base import (
    Tool,
    ToolContext,
    ToolError,
    ToolInput,
    ToolOutcome,
    cell,
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
    placeholder = "example.com"
    examples = ("example.com",)
    Input = Input

    def run(self, ctx: ToolContext, args: Input) -> ToolOutcome:
        keys = _api_keys(ctx)
        pctx = ProviderContext(
            domain=args.domain,
            timeout=TOOL_TIMEOUT,
            threads=20,
            proxy_url=None,
            api_keys=keys,
        )
        with ThreadPoolExecutor(max_workers=len(args.sources)) as pool:
            results = list(pool.map(lambda key: SOURCES[key](pctx).run(), args.sources))

        merged = merge_and_filter(results, args.domain, [])
        names = sorted(merged)
        if not names and all(r.error for r in results):
            raise ToolError(next(r.error for r in results if r.error))

        blocks = [
            table(
                ["Source", "Names", "Took", "Outcome"],
                [
                    _source_row(key, result)
                    for key, result in zip(args.sources, results, strict=True)
                ],
                title="Sources",
            ),
            table(
                ["Host", "Found by"],
                [
                    [
                        cell(name, mono=True),
                        cell(
                            ", ".join(
                                sorted(SOURCE_LABELS.get(s, s) for s in merged[name])
                            ),
                            tone=Tone.MUTED.value,
                        ),
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
                note(
                    f"First {MAX_LISTED} of {len(names)} shown.",
                    tone=Tone.INFO.value,
                )
            )

        return ToolOutcome(
            summary=_summary(
                len(names), sum(1 for r in results if not r.error and not r.skipped)
            ),
            blocks=blocks,
            caveats=[
                "Passive sources only. Bruteforce, permutations and DNS resolution "
                "require a scan."
            ],
            pivot=target_pivot_sync(ctx, args.domain),
            raw={"domain": args.domain, "hosts": names},
        )


def _summary(hosts: int, sources: int) -> str:
    return (
        f"{hosts} host{'s' if hosts != 1 else ''} from "
        f"{sources} source{'s' if sources != 1 else ''}"
    )


def _api_keys(ctx: ToolContext) -> dict[str, str | None]:
    from shared.services.api_key.sync_api_key import SyncAPIKeyService  # noqa: PLC0415

    service = SyncAPIKeyService(ctx.session)
    return {p.value: service.get_key_for_provider(p) for p in PREFETCH_KEYS}


def _source_row(key: str, result: ProviderResult) -> list:
    label = SOURCE_LABELS.get(key, key)
    if result.error:
        outcome = cell(result.error, tone=Tone.CRITICAL.value)
    elif result.skipped:
        outcome = cell(result.skip_reason or "skipped", tone=Tone.MUTED.value)
    else:
        outcome = cell(result.note or "ok", tone=Tone.SUCCESS.value)
    return [
        cell(label),
        cell(len(result.subdomains)),
        cell(f"{result.duration_seconds:.1f}s", tone=Tone.MUTED.value),
        outcome,
    ]
