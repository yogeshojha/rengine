"""Call every GET route and the read-only POST searches with real ids and boundary values."""

import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = os.environ.get("RENGINE_URL", "http://127.0.0.1:8000")
PREFIX = "/api/v1"
SLOW_SECONDS = float(os.environ.get("SLOW_SECONDS", "10"))
PAUSE = float(os.environ.get("PAUSE", "0.15"))
NIL = "00000000-0000-0000-0000-000000000000"
SKIP = re.compile(
    os.environ.get(
        "SKIP",
        r"(/stream|/auth/|/users|viewdns/reverse|issue-trackers/[^/]+/(destinations|issue-types)"
        r"|connectors/client|/download|remote-control/.*/status|/mcp|/oast|instance-settings|media/screenshot)",
    )
)
LEAK = re.compile(
    r"(Traceback|sqlalchemy|asyncpg|psycopg|/app/|\.py\b|SELECT |INSERT |UPDATE |violates|relation \")",
    re.I,
)
LONG = "a" * 5000
READ_POSTS = re.compile(
    r"/(search(/(counts|groups|leads|tabs|renders|issues))?|tree(/(hosts|leaves))?"
    r"|timeline(/renders)?|gone)$"
)
OK = 200
SERVER_ERROR = 500
UNAUTHORIZED = 401


class Client:
    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )

    def login(self) -> None:
        body = {
            "username": os.environ["RENGINE_USER"],
            "password": os.environ["RENGINE_PASSWORD"],
        }
        self.call("POST", "/auth/login", body=body)

    def call(self, method: str, path: str, query=None, body=None):
        url = BASE + PREFIX + path
        if query:
            url += "?" + urllib.parse.urlencode(query, doseq=True)
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=data, method=method, headers=headers)  # noqa: S310
        start = time.monotonic()
        try:
            with self.opener.open(req, timeout=60) as resp:
                code, raw = resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            code, raw = exc.code, exc.read()
        except OSError as exc:
            code, raw = 0, str(exc).encode()
        return code, time.monotonic() - start, raw

    def json(self, path: str, query=None, body=None, method="GET"):
        code, _, raw = self.call(method, path, query, body)
        if code != OK:
            return None
        try:
            return json.loads(raw)
        except ValueError:
            return None


def _items(payload) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "rows", "results", "threads", "runs"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def _first(payload, key="id"):
    for item in _items(payload):
        if isinstance(item, dict) and item.get(key):
            return str(item[key])
    return None


def gather(c: Client, project: str) -> dict:
    ids: dict[str, str] = {"project_id": project}
    projects = c.json("/projects") or []
    slug = next((p["slug"] for p in projects if p["id"] == project), None)
    ids["project_slug"] = slug or ""
    scans = c.json("/scans", {"project_id": project, "size": 5})
    ids["scan_id"] = _first(scans) or NIL
    scan_items = _items(scans)
    ids["current"] = ids["scan_id"]
    ids["baseline"] = next(
        (
            str(s["id"])
            for s in scan_items[1:]
            if scan_items and s.get("target_id") == scan_items[0].get("target_id")
        ),
        ids["scan_id"],
    )
    targets = c.json("/targets", {"project_slug": slug, "size": 5})
    ids["target_id"] = _first(targets) or NIL
    scope = {"project_id": project}
    for name, path in (
        ("vulnerability_id", "/vulnerabilities/search"),
        ("asset_id", "/subdomains/search"),
        ("endpoint_id", "/endpoints/search"),
        ("secret_id", "/secrets/search"),
    ):
        ids[name] = _first(c.json(path, scope, {"limit": 1}, "POST")) or NIL
    for name, path in (
        ("note_id", "/notes"),
        ("engine", "/engines"),
        ("context", "/contexts"),
        ("schedule", "/schedules"),
        ("tripwire_id", "/tripwires"),
        ("watch_id", "/bounty-programs/watches"),
        ("wordlist_id", "/wordlists"),
        ("thread_id", "/ask/threads"),
        ("estate_thread", "/ask/estate/threads"),
        ("run_id", "/toolbox/runs"),
        ("tracker_id", "/issue-trackers"),
        ("connector_id", "/connectors"),
        ("export_id", "/exports"),
        ("report_id", "/reports"),
        ("key_id", "/api-keys"),
    ):
        ids[name] = _first(c.json(path, scope)) or NIL
    return ids


def path_value(path: str, name: str, ids: dict) -> str:
    if name == "id":
        for prefix, key in (
            ("/engines", "engine"),
            ("/contexts", "context"),
            ("/schedules", "schedule"),
            ("/scans", "scan_id"),
        ):
            if path.startswith(prefix):
                return ids.get(key, NIL)
    if name == "thread_id" and path.startswith("/ask/estate"):
        return ids.get("estate_thread", NIL)
    fixed = {
        "platform": "hackerone",
        "handle": "security",
        "channel": "telegram",
        "kind": "epss" if "datasets" in path else "kev",
        "cve": "CVE-2021-44228",
        "slug": "default",
        "host": "example.com",
        "nameserver": "ns1.example.com",
        "template_id": "CVE-2021-44228",
        "block_id": "B1",
        "command_id": NIL,
        "record_id": NIL,
        "user_id": NIL,
    }
    return ids.get(name) or fixed.get(name, NIL)


def query_value(name: str, schema: dict, ids: dict):
    if name in ids:
        return ids[name]
    defaults = {
        "dimension": "web_assets",
        "name": "example.com",
        "host": "example.com",
        "fingerprint": "0" * 16,
        "cidr": "192.0.2.0/24",
        "ns": "ns1.example.com",
        "ids": ids.get("target_id", NIL),
        "q": "a",
        "path": "x",
        "destination": "x",
        "asset_key": "example.com",
        "channels": "scans",
        "target_value": "example.com",
        "base": ids.get("baseline"),
    }
    if name in defaults:
        return defaults[name]
    return _sample(schema)


def _alts(schema: dict) -> list[dict]:
    return [a for a in schema.get("anyOf", [schema]) if a.get("type") != "null"]


def _sample(schema: dict):
    for alt in _alts(schema):
        if "enum" in alt:
            return alt["enum"][0]
        kind = alt.get("type")
        if kind == "integer":
            return alt.get("minimum", 1)
        if kind == "string":
            return NIL if alt.get("format") == "uuid" else "a"
        if kind == "boolean":
            return "true"
    return "a"


def edges(schema: dict) -> list:
    out: list = []
    for alt in _alts(schema):
        kind = alt.get("type")
        if "enum" in alt or "$ref" in alt:
            out.append("bogus-value")
        elif kind == "integer":
            out += [-1, 0, 2**63, 10**30]
            if "maximum" in alt:
                out.append(int(alt["maximum"]))
        elif kind == "number":
            out += ["nan", "inf", "-1e309"]
        elif kind == "string" and alt.get("format") in ("date-time", "date"):
            out += ["2026-01-01T00:00:00", "0001-01-01", "9999-12-31T23:59:59+14:00"]
        elif kind == "string" and alt.get("format") != "uuid":
            out += ["%", "'", LONG]
        elif kind == "array":
            out.append(["bogus-value", "%"])
    return out


def resolve(spec: dict, schema: dict) -> dict:
    ref = schema.get("$ref")
    if ref:
        return spec["components"]["schemas"][ref.rsplit("/", 1)[-1]]
    return schema


def cases_for(spec: dict, op: dict, ids: dict):
    params = op.get("parameters", [])
    query = {
        p["name"]: query_value(p["name"], p.get("schema", {}), ids)
        for p in params
        if p["in"] == "query" and (p.get("required") or p["name"] == "project_id")
    }
    body_schema = (
        op.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    body = None
    props: dict = {}
    if body_schema is not None:
        body_schema = resolve(spec, body_schema)
        props = body_schema.get("properties", {})
        body = {
            name: _sample(resolve(spec, props[name]))
            for name in body_schema.get("required", [])
            if name in props
        }
    yield "base", query, body
    for p in params:
        if p["in"] != "query" or p.get("required") or p["name"] in ids:
            continue
        for value in edges(p.get("schema", {})):
            yield f"{p['name']}={str(value)[:24]}", {**query, p["name"]: value}, body
    for name, prop in props.items():
        for value in edges(resolve(spec, prop)):
            yield f"body.{name}={str(value)[:24]}", query, {**(body or {}), name: value}


def main() -> int:
    spec_path, project = sys.argv[1], sys.argv[2]
    spec = json.loads(Path(spec_path).read_text())
    c = Client()
    c.login()
    ids = gather(c, project)
    print("ids", json.dumps(ids), flush=True)
    findings = 0
    for full, ops in sorted(spec["paths"].items()):
        if not full.startswith(PREFIX):
            continue
        path = full[len(PREFIX) :]
        if SKIP.search(path):
            continue
        for method in ("get", "post"):
            op = ops.get(method)
            if not op or (method == "post" and not READ_POSTS.search(path)):
                continue
            for label, query, body in cases_for(spec, op, ids):
                concrete = re.sub(
                    r"\{([^}]+)\}",
                    lambda m, p=path: path_value(p, m.group(1), ids),
                    path,
                )
                code, took, raw = c.call(method.upper(), concrete, query, body)
                text = raw[:400].decode("utf-8", "replace")
                bad = code >= SERVER_ERROR or code == 0 or took > SLOW_SECONDS
                leak = code != OK and LEAK.search(text)
                if bad or leak:
                    findings += 1
                    print(
                        f"{code} {took:.1f}s {method.upper()} {concrete} [{label}] "
                        f"{text[:200]!r}",
                        flush=True,
                    )
                if code == UNAUTHORIZED:
                    c.login()
                time.sleep(PAUSE)
    print("findings", findings)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
