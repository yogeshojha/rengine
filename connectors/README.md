# Connectors

A connector receives proxied traffic from a web proxy and records it twice: as request shapes on
the Connectors page, and as `endpoints` rows of the target's covering scan, with source `proxy`.
The Endpoints page, the query grammar (`source:proxy`), reports and MCP see the browsing the same
way they see a crawl.

One connector ships: **Burp Suite** (Montoya extension, Community and Professional). The built jar
is served at `GET /api/v1/connectors/client/burp` from `binaries/`.

## The contract

```
POST /api/v1/connectors/ingest
Authorization: Bearer rngconn_…

{"client": "burp-connector/0.1.0", "items": [
  {"url": "https://target/admin/", "method": "GET", "status_code": 200,
   "authenticated": true, "source_tool": "proxy", "body_params": ["id"]}
]}
```

The response reports `accepted`, `novel` (new shapes), `dropped`, `queued`, `recorded` (endpoint
rows written) and the shapes flagged for review.

## What happens to a batch

1. **Shape.** `shared/definitions/endpoints.py:shape_for` collapses identifier-looking segments, so
   `/api/users/1234` and `/api/users/9999` resolve to one row. Endpoints carry the same `shape`
   column, computed at write.
2. **Fold.** `connectors/ingest.py` merges every item sharing a signature: the path shape plus its
   parameter names.
3. **Scope.** The server resolves each host to a target. Unmatched hosts are recorded as unassigned
   and attach when a target appears.
4. **Known.** A shape is known when a scan recorded the same host and shape, whatever the scheme,
   port or parameter set. Parameters no scan saw raise `new_params`. `unseen_by_scans` is raised only
   when a settled census scan covers the target.
5. **Record.** `shared/services/proxy_sync.py` writes the shapes into the target's covering scan.
   A target with no census scan gets a `Browsing · <connector>` run. While a census scan is running
   the rows wait; finalize replays every recorded shape of the target into it.
6. **Notice.** `connectors/notice.py` derives why a shape warrants review from stored data only.

## Adding a connector

One directory under `connectors/`, auto-discovered. No registry edit.

```
connectors/<name>/
  __init__.py
  connector.py   # a ProxyConnector subclass
```

Set `kind` (a `ConnectorKind` member), `title`, `vendor`, `description` and `client_file` (a file
under `binaries/`), and return the setup steps from `setup()`.

The vocabulary is one file: `shared/definitions/connectors.py`, mirrored by
`frontend/src/lib/config/connectors.ts`.
