# reNgine MCP server

A Model Context Protocol server over the attack surface reNgine has mapped. A
token with the launch capability also starts scans.

Everything MCP lives in this directory. Adding a tool needs no file outside it.

- **Start, stop, agents and activity:** the **Agents** page.
- **Adding a tool:** [ADDING_A_TOOL.md](ADDING_A_TOOL.md).

---

## Connecting

Add an agent on the Agents page. The connect sheet shows the configuration for
each supported client with the key filled in.

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

The stdio transport, for an agent that launches the process itself:

```
docker compose exec -T -e RENGINE_MCP_TOKEN api /app/.venv/bin/python -m mcp.stdio
```

with `RENGINE_MCP_TOKEN` in its environment. Both transports apply the same
token permissions.

### Capabilities

A token holds a subset of four capabilities. The instance sets a ceiling no token
exceeds. `tools/list` returns only the tools a token may call.

| Capability | Grants | Reaches the target |
|---|---|---|
| `read` | Query assets, services, endpoints, findings and coverage | No |
| `plan` | Resolve a scan plan without running it | No |
| `write` | Add, change and delete targets. Record triage decisions | No |
| `launch` | Start, pause, resume and cancel scans and focused rescans | **Yes** |

`read` is always granted. `launch` is off at the instance ceiling by default.

---

## Tools

Twenty-six tools. Arguments in **bold** are required.

### Orient

| Tool | Needs | Arguments |
|---|---|---|
| `resolve_target` | read | **target** |
| `surface_brief` | read | **target**, dimension, include_empty |
| `describe_query_language` | read | dimension, fields_only |
| `list_targets` | read | contains, limit |
| `list_projects` | read | none |
| `list_engines` | read | contains, project_id, limit |
| `list_contexts` | read | project_id, limit |
| `scan_status` | read | scan, target, limit |

### Interrogate

| Tool | Needs | Arguments |
|---|---|---|
| `query_assets` | read | target, dimension, query, limit, offset, project_id |
| `group_assets` | read | **target**, dimension, **group_by**, query |
| `what_changed` | read | window, project_id |
| `compare_runs` | read | target, current, baseline, dimension |
| `cve_exposure` | read | **cve**, target, project_id |
| `domain_posture` | read | **target**, failing_only |

### Explain

| Tool | Needs | Arguments |
|---|---|---|
| `explain_finding` | read | **target**, **finding** |
| `scan_coverage` | read | **target**, dimension |

### Act

| Tool | Needs | Arguments |
|---|---|---|
| `plan_scan` | plan | **target**, engine_id, stages, intensity, project_id |
| `start_scan` | launch | **target**, engine_id, stages, intensity, context_id, project_id |
| `focused_rescan` | launch | **target**, **dimension**, **assets**, stages |
| `pause_scan` | launch | scan, target |
| `resume_scan` | launch | scan, target |
| `cancel_scan` | launch | scan, target |
| `record_triage` | write | **target**, **fingerprint**, **state**, note |
| `add_target` | write | **targets**, project_id, tags, organizations |
| `update_target` | write | **target**, display_name, tags, organizations |
| `delete_target` | write | **target**, confirm |

Every result carries `open_in_rengine`. The count a tool reports equals the rows
that link opens. A dimension no scan covered is reported as not covered, not as
zero. A result holding text written by a scanned system is flagged
`untrusted_content`.

`delete_target` is the one tool with `destructiveHint` set. Called without
`confirm=true` it deletes nothing and returns what the delete would remove.

---

## Layout

```
mcp/
  capabilities.py   what a token may do, mirrored by the frontend
  auth.py           token minting, hashing and header parsing. Only the hash is stored
  models.py         the mcp_tokens table and the API's read and write shapes
  settings.py       server settings, stored on instance_settings
  service.py        settings, tokens, status and authentication for the API
  clients.py        setup snippets per MCP client
  protocol.py       JSON-RPC framing and the MCP method names
  server.py         dispatch: a parsed request plus a context becomes a response
  transport.py      one entry point: authenticate, rate-limit, dispatch
  stdio.py          the stdio transport
  context.py        the session, token identity and scope a tool receives
  errors.py         errors and their JSON-RPC codes
  result.py         what a tool returns
  registry.py       every discovered tool, validated and described
  dimensions.py     the result dimensions, adapted for tools
  links.py          deep links into the UI
  phrasing.py       short spellings for a chat screen
  limits.py         per-token call ceiling, fail-open
  telemetry.py      live sessions and the recent-call trail in Redis, fail-open
  tools/            one file per tool, discovered automatically
```

`protocol.py` is the only module that knows the wire format. No MCP SDK is used.

This package is named `mcp` and shadows the `mcp` package on PyPI. Rename it
before adding that package as a dependency.
