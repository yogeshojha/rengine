# Adding a tool

One file in `mcp/tools/`. No registry to edit, no route to add, no frontend
change. Drop the file in, restart the api, and the tool appears in `tools/list`,
in the MCP page's Tools tab, and in every agent connected with a token that
carries its capability.

## The smallest possible tool

`mcp/tools/count_targets.py`:

```python
from mcp.context import ToolContext
from mcp.result import ToolResult
from mcp.tools.base import Tool, ToolGroup, ToolInput


class Input(ToolInput):
    pass


class CountTargets(Tool):
    name = "count_targets"
    title = "Count targets"
    description = "How many targets this token can see."
    Input = Input

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:
        return ToolResult(summary="12 targets")
```

That is the whole contract. Everything else is optional.

## The full contract

```python
class MyTool(Tool):
    name: str  # snake_case, unique across the server
    title: str  # short human label, shown in the UI
    description: str  # what the MODEL reads — write it for the model
    capability = Capability.READ  # read | plan | write | launch
    group = ToolGroup.INTERROGATE  # Orient | Interrogate | Explain | Act
    destructive = False  # True if the call destroys data; sets destructiveHint
    Input: type[ToolInput]  # pydantic model; becomes the JSON Schema
    examples: tuple[str, ...]  # shown in the UI and docs, never to the model

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult: ...
```

**`Input` is the single source of truth for arguments.** `model_json_schema()`
becomes the `inputSchema` the model plans against, and the server validates every
call with it before your `run` is reached — so `args` is always valid.
`Field(description=...)` is the only place an argument is explained; do not
restate it in the tool description.

```python
class Input(ToolInput):
    target: str = Field(description="A domain, address or ASN already in reNgine.")
    limit: int = Field(default=20, ge=1, le=100, description="Rows to return.")
```

**`capability` is the security gate.** The server checks it before calling you,
`tools/list` hides tools a token cannot use, and the instance ceiling can switch
a whole capability off. Anything that sends traffic to a target must be
`Capability.LAUNCH`; anything that writes to the database must be at least
`Capability.WRITE`.

## What you get: `ctx`

```python
ctx.session  # AsyncSession — call app.services.* directly
ctx.token  # name, project_id, capabilities, issued_by
ctx.ui_base_url  # for building links
ctx.client  # the connected agent's name

ctx.require("launch")  # raise unless the token may do this
ctx.scoped_projects()  # [project_id], or None for every project
ctx.check_project(project_id)  # raise if outside the token's scope
```

Import reNgine services *inside* `run`, not at module scope — a tool module that
fails to import is skipped with a warning rather than breaking discovery:

```python
async def run(self, ctx, args):
    from app.services.subdomain import SubdomainService  # noqa: PLC0415
```

## What you return: `ToolResult`

```python
ToolResult(
    summary="33 services match on gov.cy",  # one line the model should say
    data={...},  # structured payload it may quote
    pivot=links.scan_tab(ctx.ui_base_url, scan_id, "services", query),
    caveats=["Observed 4 Sep by scan d67fb42…"],
    untrusted=True,  # rows contain target-written text
)
```

Three of these carry reNgine's contract, and a tool that skips them is a worse
tool:

- **`pivot`** — the count is a promise. Whatever number is in `summary`, the link
  must open exactly those rows. If you cannot produce such a link, do not report
  a count.
- **`caveats`** — say what the answer cannot tell you: a capped total, a
  dimension that was never scanned, a figure from an older run.
- **`untrusted`** — set it whenever `data` contains anything the scanned party
  wrote (titles, banners, bodies, certificate subjects). It adds the instruction
  that stops the model treating that text as a command.

## Errors

Raise `ToolError` with a message written for the model. It comes back as a tool
error the agent can act on, not a transport failure — and a good message teaches:

```python
raise ToolError(
    f"{dim.label} cannot be grouped by {key!r}. Try one of: {', '.join(keys)}."
)
```

Anything else you raise is logged and returned as a generic failure, so prefer
`ToolError` wherever the caller could do something about it.

## Working with the five dimensions

If your tool is per-dimension, use the adapter rather than branching:

```python
from mcp.dimensions import dimension
from mcp.tools._scope import resolve

dim = dimension(
    args.dimension
)  # web_assets | ips | services | vulnerabilities | endpoints
scope = await resolve(ctx, args.target)  # target + per-dimension coverage
scan_id = scope.require(dim)  # raises with the "never scanned" message

f = dim.build_filter(args.query, limit=args.limit, offset=args.offset)
page = await dim.search(ctx.session, scan_id, f, scope.project_id)
rows = [dim.compact(row) for row in page.items]
```

`scope.require(dim)` is what stops a tool reporting "0 findings" for a dimension
nobody ever scanned. Use it rather than reaching for a scan id yourself.

## Checklist

- [ ] `name` is unique and snake_case
- [ ] `description` is written for the model, and says when to call it
- [ ] every `Input` field has a `description`
- [ ] `capability` is `launch` if it touches a target, `write` if it writes
- [ ] `destructive` is set if the call destroys data, and `run` refuses without an explicit confirm
- [ ] `pivot` is set wherever a count is reported
- [ ] `untrusted=True` wherever target-written text is returned
- [ ] `ruff check mcp` passes

Then restart the api and confirm:

```bash
docker compose exec -T api /app/.venv/bin/python -c \
  "from mcp.registry import registry; print(sorted(registry()))"
```
