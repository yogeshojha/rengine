# reNgine MCP server

Lets a language-model agent interrogate an attack surface reNgine has already
mapped — and, if you allow it, start scans.

Everything MCP lives in this directory. Turn the server on, issue a token and
paste it into your agent; nothing else is configured, and no file outside this
package needs editing to add a tool.

- **Start / stop, tokens and activity:** the **MCP** page in reNgine.
- **Adding your own tool:** [ADDING_A_TOOL.md](ADDING_A_TOOL.md).

---

## What makes this server different

Most recon MCP servers expose one verb: *go run a scan*. This one is built the
other way round, because reNgine's value is the correlated result set, not the
scanner. Four properties are carried into every answer:

**The count is a promise.** Every result carries `open_in_rengine`. The number a
tool reports equals the number of rows that link opens, because both go through
the same filter and compiler the UI uses. An agent can never quote a figure a
human cannot verify in one click.

**Not scanned is not zero.** `resolve_target` reports `covered` per dimension.
A scan that enumerated hostnames but never probed them has zero live hosts *and*
never looked — those are different facts, and the tools refuse to conflate them.

**New needs a baseline.** `is:new` is `has_baseline AND NOT seen_earlier`
everywhere, so a target's first scan never reports its whole surface as new.

**Rows are untrusted input.** Response bodies, page titles, service banners and
certificate subjects are written by the scanned party. Results that contain them
are flagged `untrusted_content`, and the server's instructions tell the model to
report them, never to follow them.

---

## Connecting

Issue a token on the MCP page, choose **Copy client config**, and paste it into
your agent. That is the whole setup.

```json
{
  "mcpServers": {
    "rengine": {
      "type": "http",
      "url": "http://localhost:5173/api/v1/mcp",
      "headers": { "Authorization": "Bearer rngmcp_…" }
    }
  }
}
```

For an agent that prefers to launch the process itself:

```
docker compose exec -T api /app/.venv/bin/python -m mcp.stdio
```

with `RENGINE_MCP_TOKEN` in its environment. Permissions are identical on both
transports — they are a property of the token, not the pipe.

### Capabilities

A token carries a subset of four capabilities, and the instance sets a ceiling
no token may exceed. `tools/list` returns only the tools a token may call, so an
agent never sees a tool it cannot use.

| Capability | Grants | Reaches the target |
|---|---|---|
| `read` | Query assets, services, endpoints, findings, coverage | No |
| `plan` | Resolve a scan plan without running it | No |
| `write` | Add, label and delete targets; record triage decisions | No |
| `launch` | Start scans and focused rescans | **Yes** |

`read` is always granted. `launch` is off by default at the instance ceiling.

---

## The default tools

Seventeen tools, roughly 3,600 tokens of definitions for a full-capability token.
Arguments in **bold** are required.

### Orient — turn a name into something you can query

| Tool | Needs | Arguments |
|---|---|---|
| `resolve_target` | read | **target** |
| `surface_brief` | read | **target**, dimension, include_empty |
| `describe_query_language` | read | dimension, fields_only |
| `list_targets` | read | contains, limit |
| `list_projects` | read | — |

**`resolve_target`** is the keystone. Every result endpoint in reNgine is
scan-scoped, and picking the newest scan is wrong. This resolves, per dimension,
the most recent scan that actually covered it — plus the count, when it was
observed, and the change against the previous covering run. Every other tool
takes its scan from here.

**`surface_brief`** is the fastest way to learn what is interesting. It returns
reNgine's curated query library with a real count against each entry for this
scan, ranked so the discriminating queries come first. One call, and the agent
knows where to look instead of guessing:

```
class:database                        3    Data stores reachable from the internet
is:sensitive and not is:cdn          33    Administrative ports on an origin address
class:remote                          8    Interactive administration reachable
service:[telnet,ftp,rlogin,rexec]     6    Protocols that carry credentials in the clear
```

**`describe_query_language`** returns the exact grammar for one dimension. It is
a tool rather than part of a tool description because all five grammars together
are about 16,600 tokens — far too much to carry on every turn, and exact when
fetched.

### Interrogate — ask the question

| Tool | Needs | Arguments |
|---|---|---|
| `query_assets` | read | **target**, dimension, query, limit, offset |
| `group_assets` | read | **target**, dimension, **group_by**, query |
| `what_changed` | read | window, project_id |

**`query_assets`** is one tool over all five dimensions. Rows are trimmed to the
columns that carry meaning — a raw row costs about 205 tokens, a trimmed one
about 25 — and the exact total always comes back with the link that proves it.

**`group_assets`** counts by technology, status, ASN, country, severity, service
class and so on. Each group carries the query that isolates it, so drilling in
lands on exactly that count.

**`what_changed`** is the cross-target digest: what is new per target over a
window, which dimensions a run covered for the first time, and which targets have
never been scanned or have gone stale.

### Explain — turn a row into an answer

| Tool | Needs | Arguments |
|---|---|---|
| `explain_finding` | read | **target**, **finding** |
| `scan_coverage` | read | **target**, dimension |

**`explain_finding`** takes a template id, check name, CVE or fingerprint and
returns what the check tests for, why it matters, how to fix it, its CVE / CWE /
CVSS / EPSS / KEV signals, every place it fires, and the current review decision.

**`scan_coverage`** is the scanner's own account: checks selected against checks
loaded, hosts scanned, requests sent, hosts given up on. A null count means the
scanner did not report that number — never that it was zero. This is what keeps
"no findings" honest.

### Act — capability-gated

| Tool | Needs | Arguments |
|---|---|---|
| `plan_scan` | plan | **target**, engine_id, stages, intensity |
| `start_scan` | launch | **target**, engine_id, stages, intensity, context_id |
| `focused_rescan` | launch | **target**, **dimension**, **assets**, stages |
| `record_triage` | write | **target**, **fingerprint**, **state**, note |
| `add_target` | write | **targets**, project_id, tags, organizations |
| `update_target` | write | **target**, display_name, tags, organizations |
| `delete_target` | write | **target**, confirm |

**`plan_scan`** resolves which stages would run, which are skipped and why, the
footprint and the estimated duration, without contacting the target at all.

**`focused_rescan`** is the loop that makes an agent useful: query, pick the
interesting rows, re-probe just those as their own run, read the result. The run
is recorded separately and does not disturb the parent scan's totals.

**`record_triage`** makes an agent's judgement durable. The decision is keyed to
the finding's fingerprint, so a false positive stays suppressed on every later
scan of that target.

**`add_target`** records a target and queues its WHOIS, DNS and routing
enrichment. It sends no traffic — a target reNgine knows about is not a target
reNgine has scanned, and every dimension reads as never scanned until a scan
runs. A value already in the project is reused, so an agent that re-adds its
working set does not duplicate it.

**`delete_target`** is the one tool that destroys data, and it is the only one
whose `destructiveHint` is true. Called without `confirm` it refuses, and
answers with what would be lost — the number of scans and what they hold — so
the agent has something to put in front of a person before asking again.

---

## Layout

```
mcp/
  capabilities.py   what a token may do — one definition, mirrored by the frontend
  auth.py           minting, hashing and header parsing; reNgine keeps only the hash
  models.py         the mcp_tokens table and the API's read/write shapes
  settings.py       server settings, stored on instance_settings
  service.py        settings, tokens, status, authentication — what the API calls
  protocol.py       JSON-RPC framing and the MCP method names. No transport, no DB
  server.py         dispatch: a parsed request plus a context becomes a response
  transport.py      one entry point: authenticate, rate-limit, dispatch
  stdio.py          the stdio transport
  registry.py       every discovered tool, validated and described
  dimensions.py     the five result dimensions, adapted for tools
  links.py          deep links back into the UI
  limits.py         per-token call ceiling (fail-open)
  telemetry.py      live sessions and the recent-call trail (Redis, fail-open)
  tools/            one file per tool, discovered automatically
```

The wire protocol is implemented directly rather than through an SDK: a
tools-only MCP server is a small JSON-RPC surface, and it keeps this package
dependency-free. `protocol.py` is the only module that knows the wire format, so
swapping in an SDK later touches one file.

Note that this package is named `mcp`, which shadows the `mcp` package on PyPI.
That is deliberate — reNgine does not use it — but do not add it as a dependency
without renaming this package first.
