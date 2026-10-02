# Adding a tool

One file in `mcp/tools/`. No registry edit, no route and no frontend change.
After an api restart the tool appears in `tools/list`, in the Tools sheet on the
Agents page, and to every agent whose token carries its capability.

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

`name`, `title`, `description` and `run` are required. Every other attribute has
a default.

## The full contract

```python
class MyTool(Tool):
    name: str  # snake_case, unique across the server
    title: str  # short label shown in the UI
    description: str  # the text the model reads
    capability = Capability.READ.value  # read, plan, write or launch
    group = ToolGroup.INTERROGATE.value  # Orient, Interrogate, Explain or Act
    destructive = False  # the call destroys data; sets destructiveHint
    command = None  # one short word for chat; None keeps the tool out of chat
    value_field = ""  # the Input field a bare chat argument fills
    Input: type[ToolInput]  # pydantic model; becomes the JSON Schema
    examples: tuple[str, ...]  # shown in the UI and docs, not to the model

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult: ...
```

**`Input` is the single source of truth for arguments.** `model_json_schema()`
becomes the `inputSchema` the model plans against, and the server validates every
call with it before `run` is reached. `Field(description=...)` is the one place
an argument is explained. The tool description does not restate it.

The registry refuses a `command` outside `^[a-z][a-z0-9]{1,15}$`, a command two
tools share, and a `value_field` that names no `Input` field.

```python
class Input(ToolInput):
    target: str = Field(description="A domain, address or ASN already in reNgine.")
    limit: int = Field(default=20, ge=1, le=100, description="Rows to return.")
```

**`capability` is the security gate.** The server checks it before `run`,
`tools/list` hides tools a token cannot use, and the instance ceiling can switch
a whole capability off. A tool that sends traffic to a target is
`Capability.LAUNCH.value`. A tool that writes to the database is at least
`Capability.WRITE.value`.

## The context: `ctx`

```python
ctx.session  # AsyncSession, for app.services.* calls
ctx.token  # name, project_id, capabilities, issued_by
ctx.ui_base_url  # for building links
ctx.client  # the connected agent's name

ctx.require("launch")  # raise unless the token may do this
ctx.scoped_projects()  # [project_id], or None for every project
ctx.check_project(project_id)  # raise if outside the token's scope
```

`mcp/tools/_scope.py` holds the shared helpers: `project_for` picks the project a
project-wide tool acts on, `parse_id` reads a UUID argument and `operator`
returns the user a change is attributed to.

Import reNgine services inside `run`, not at module scope. A tool module that
fails to import is skipped with a warning and discovery continues:

```python
async def run(self, ctx, args):
    from app.services.subdomain import SubdomainService  # noqa: PLC0415
```

## The result: `ToolResult`

```python
ToolResult(
    summary="33 services match on gov.cy",  # one line the model should say
    data={...},  # structured payload it may quote
    pivot=links.scan_tab(ctx.ui_base_url, scan_id, "services", query),
    caveats=["Observed 4 Sep by scan d67fb42…"],
    untrusted=True,  # rows contain target-written text
)
```

Three fields carry reNgine's contract:

- **`pivot`**: the count is a promise. The link opens exactly the rows the
  number in `summary` counts. A tool with no such link reports no count.
- **`caveats`**: what the answer cannot state, such as a capped total, a
  dimension that was not scanned or a figure from an older run.
- **`untrusted`**: set whenever `data` holds text the scanned party wrote, such
  as titles, banners, bodies and certificate subjects. It adds the instruction
  that keeps the model from treating that text as a command.

## Errors

Raise `ToolError` with a message written for the model. It returns as a tool
error the agent can act on, not a transport failure:

```python
raise ToolError(
    f"{dim.label} cannot be grouped by {key!r}. Try one of: {', '.join(keys)}."
)
```

Any other exception is logged and returned as `<title> failed: <message>`.
`ToolError` is the right type wherever the caller can act on the message.

## Working with result dimensions

A per-dimension tool uses the adapter instead of branching:

```python
from mcp.dimensions import dimension
from mcp.tools._scope import resolve

# web_assets, ips, services, vulnerabilities, endpoints or secrets
dim = dimension(args.dimension)
scope = await resolve(ctx, args.target)  # target and per-dimension coverage
scan_id = scope.require(dim)  # raises when the dimension was not scanned

f = dim.build_filter(args.query, limit=args.limit, offset=args.offset)
page = await dim.search(ctx.session, scan_id, f, scope.project_id)
rows = [dim.compact(row) for row in page.items]
```

`scope.require(dim)` keeps a tool from reporting "0 findings" for a dimension no
scan covered. A tool takes its scan id from it.

## Checklist

- [ ] `name` is unique and snake_case
- [ ] `description` is written for the model, and says when to call it
- [ ] every `Input` field has a `description`
- [ ] `capability` is `launch` if it touches a target, `write` if it writes
- [ ] `destructive` is set if the call destroys data, and `run` refuses without an explicit confirm
- [ ] `pivot` is set wherever a count is reported
- [ ] `untrusted=True` wherever target-written text is returned
- [ ] `ruff check mcp` passes

After an api restart, confirm the tool is registered:

```bash
docker compose exec -T api /app/.venv/bin/python -c \
  "from mcp.registry import registry; print(sorted(registry()))"
```
