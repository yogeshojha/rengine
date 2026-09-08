# Connectors

A connector receives proxied traffic from a web proxy and records it as request shapes. Shapes are
classified and flagged without sending a request; scanning them is a separate, explicit step.

Two connectors ship: **Burp Suite** (Montoya extension, supported on Community and Professional) and
**Caido** (plugin, or any client posting the same batch).

## The contract

```
POST /api/v1/connectors/ingest
Authorization: Bearer rngconn_…

{"client": "burp/2026.4.2", "items": [
  {"url": "https://target/admin/", "method": "GET", "status_code": 200,
   "authenticated": true, "source_tool": "proxy", "body_params": ["id"]}
]}
```

The response reports accepted, novel and dropped counts, the shapes flagged for review, and whether
the queue meets its scan trigger.

## What happens to a batch

1. **Shape.** `connectors/shape.py` collapses identifier-looking path segments, so
   `/api/users/1234` and `/api/users/9999` resolve to one row.
2. **Fold.** `connectors/ingest.py` merges every item sharing a signature: the path shape plus its
   parameter names, the same identity used in `shared/definitions/endpoints.py`.
3. **Scope.** The server enforces scope, not the client. Out-of-scope hosts are discarded before
   anything is written, including the session record.
4. **Notice.** `connectors/notice.py` derives why a shape warrants review, from stored data only. It
   sends no request.
5. **Queue.** Shapes are recorded as candidates. Dispatching them as a scan is a separate step.

## Adding a connector

One directory under `connectors/`, auto-discovered — no registry edit.

```
connectors/<name>/
  __init__.py
  connector.py   # a ProxyConnector subclass
```

Set `kind` (a `ConnectorKind` member), `title`, `vendor` and `description`, and return the setup
steps from `setup(endpoint=…, secret=…)`. A module that fails to import is skipped with a warning
rather than breaking discovery.

The vocabulary is one file: `shared/definitions/connectors.py`, mirrored by
`frontend/src/lib/config/connectors.ts`.
