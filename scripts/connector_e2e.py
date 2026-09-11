#!/usr/bin/env python3
"""End-to-end check of the Connectors feature, driven entirely through the HTTP API."""

from __future__ import annotations

import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("RENGINE_API", "http://localhost:8000/api/v1")
PID = os.environ.get("RENGINE_PROJECT_ID", "")
USER = os.environ.get("RENGINE_USER", "rengine")
PASSWORD = os.environ.get("RENGINE_PASSWORD", "rengine@123")

OK = 200
CREATED = 201
NO_CONTENT = 204
BAD_REQUEST = 400
UNAUTHORIZED = 401
NOT_FOUND = 404
TOO_MANY = 429
TOKEN_ATTEMPTS = 25
TOKEN_LENGTH = 8 + 48
FOLDED_SHAPES = 2
FOLDED_WITH_OFFSITE = 3
MIN_HITS = 6
EXPECTED_SETUP_STEPS = 2

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

passed, failed = [], []


def call(method, path, body=None, token=None, raw=False):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)  # noqa: S310
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with opener.open(req) as r:
            payload = r.read()
            return r.status, (json.loads(payload) if payload and not raw else None)
    except urllib.error.HTTPError as e:
        payload = e.read()
        try:
            return e.code, json.loads(payload)
        except Exception:
            return e.code, None


def check(name, cond, detail=""):
    (passed if cond else failed).append(name)
    print(
        ("  PASS  " if cond else "  FAIL  ")
        + name
        + (f"   [{detail}]" if detail and not cond else "")
    )


print("== auth ==")
s, _ = call("POST", "/auth/login", {"username": "rengine", "password": "rengine@123"})
check("login", s == OK, s)

s, tpage = call("GET", f"/targets?project_id={PID}&size=50")
targets = tpage.get("items", tpage) if isinstance(tpage, dict) else tpage
HOST = next(
    (t["target_value"] for t in targets if t.get("target_type") == "domain"), None
)
check(
    "a domain target exists to test scope against",
    HOST is not None,
    "add one domain target",
)
if HOST is None:
    raise SystemExit(1)
print(f"   using target {HOST}")

print("\n== catalog ==")
s, cat = call("GET", "/connectors/catalog")
check(
    "catalog lists both connectors",
    s == OK and {c["kind"] for c in cat} == {"burp"},
    cat,
)
check(
    "catalog carries setup metadata",
    all(c["title"] and c["vendor"] and c["tools"] for c in cat),
)

print("\n== create ==")
s, created = call(
    "POST",
    "/connectors",
    {
        "name": "e2e burp",
        "kind": "burp",
        "project_id": PID,
        "sync_trigger": "manual",
    },
)
check("create returns 201", s == CREATED, s)
secret = created["secret"]
cid = created["connector"]["id"]
check(
    "secret is returned once and is prefixed",
    secret.startswith("rngconn_") and len(secret) == TOKEN_LENGTH,
)
check("setup steps included", len(created["setup"]["steps"]) >= EXPECTED_SETUP_STEPS)
check("state starts idle", created["connector"]["state"] == "idle")

s, _ = call("POST", "/connectors", {"name": "x", "kind": "nope", "project_id": PID})
check("unknown kind rejected", s == BAD_REQUEST, s)
s, _ = call("GET", "/connectors/targets")
check("the target picker needs a token", s == UNAUTHORIZED, s)

print("\n== ingest auth ==")
s, _ = call("POST", "/connectors/ingest", {"items": []})
check("no token rejected", s == UNAUTHORIZED, s)
s, _ = call("POST", "/connectors/ingest", {"items": []}, token="rngconn_" + "0" * 48)
check("wrong token rejected", s == UNAUTHORIZED, s)

print("\n== ingest: scope, tools, static, folding ==")
batch = {
    "client": "burp/2026.4.2",
    "items": [
        {
            "url": f"https://{HOST}/api/v3/items/111",
            "method": "GET",
            "status_code": 200,
            "authenticated": True,
            "source_tool": "proxy",
        },
        {
            "url": f"https://{HOST}/api/v3/items/222",
            "method": "GET",
            "status_code": 200,
            "authenticated": True,
            "source_tool": "proxy",
        },
        {
            "url": f"https://{HOST}/api/v3/items/333",
            "method": "GET",
            "status_code": 200,
            "authenticated": True,
            "source_tool": "proxy",
        },
        {
            "url": f"https://{HOST}/wp-admin/",
            "method": "GET",
            "status_code": 200,
            "source_tool": "proxy",
        },
        {
            "url": f"https://{HOST}/logo.png",
            "method": "GET",
            "status_code": 200,
            "content_type": "image/png",
            "source_tool": "proxy",
        },
        {
            "url": f"https://{HOST}/x?q=1",
            "method": "GET",
            "status_code": 200,
            "source_tool": "scanner",
        },
        {
            "url": f"https://{HOST}/y?q=1",
            "method": "GET",
            "status_code": 200,
            "source_tool": "intruder",
        },
        {
            "url": "https://github.com/settings",
            "method": "GET",
            "status_code": 200,
            "source_tool": "proxy",
        },
        {"url": "not a url at all", "method": "GET", "source_tool": "proxy"},
    ],
}
s, r = call("POST", "/connectors/ingest", batch, token=secret)
check("ingest accepted", s == OK, s)
check(
    "three ids folded to one shape",
    r["accepted"] == FOLDED_WITH_OFFSITE,
    f"accepted={r['accepted']}",
)
s, offsite = call("GET", f"/connectors/{cid}/candidates?project_id={PID}&search=github")
offsite_rows = (offsite or {}).get("rows", [])
check(
    "an off-project host is kept, not dropped",
    len(offsite_rows) == 1 and offsite_rows[0]["target_id"] is None,
    offsite_rows,
)
check("novel equals accepted on first sight", r["novel"] == r["accepted"])
check("manual trigger never reports ready", r["ready"] is False)
loud = {f["url"] for f in r["flagged"]}
check("admin path flagged", any("wp-admin" in u for u in loud), loud)

print("\n== idempotency ==")
s, r2 = call("POST", "/connectors/ingest", batch, token=secret)
check("re-ingest creates nothing new", r2["novel"] == 0, f"novel={r2['novel']}")
check("re-ingest still accepts", r2["accepted"] == FOLDED_WITH_OFFSITE)

print("\n== control characters are scrubbed, never stored ==")
NUL = chr(0)
s, scrubbed = call(
    "POST",
    "/connectors/ingest",
    {
        "client": "burp" + NUL + "x",
        "items": [
            {
                "url": f"https://{HOST}/nul" + NUL + "probe",
                "method": "GE" + NUL + "T",
                "status_code": 200,
                "title": "ti" + NUL + "tle",
                "content_type": "text/ht" + NUL + "ml",
                "source_tool": "proxy",
                "body_params": ["a" + NUL + "b"],
            }
        ],
    },
    token=secret,
)
check("a NUL anywhere in the payload is accepted, not a 500", s == OK, s)
s, nul_rows = call("GET", f"/connectors/{cid}/candidates?project_id={PID}&search=nul")
stored = json.dumps((nul_rows or {}).get("rows", []))
check(
    "no NUL reaches storage",
    NUL not in stored and "\\u0000" not in stored,
    stored[:160],
)

print("\n== read paths ==")
s, page = call("GET", f"/connectors/{cid}/candidates?project_id={PID}")
paths = [row["path"] for row in page["rows"]]
check("shape stored templated", "/api/v3/items/{id}" in paths, paths)
check("static image not stored", not any(p.endswith(".png") for p in paths), paths)
check(
    "scanner and fuzzer traffic not stored",
    not any(p in ("/x", "/y") for p in paths),
    paths,
)
check(
    "hits counted on the folded shape",
    any(
        r["path"] == "/api/v3/items/{id}" and r["hits"] >= MIN_HITS
        for r in page["rows"]
    ),
    [(r["path"], r["hits"]) for r in page["rows"]],
)
s, filt = call("GET", f"/connectors/{cid}/candidates?project_id={PID}&notice=admin")
check(
    "notice filter works",
    filt["total"] >= 1 and all("admin" in r["notices"] for r in filt["rows"]),
)
s, srch = call("GET", f"/connectors/{cid}/candidates?project_id={PID}&search=wp-admin")
check("search filter works", srch["total"] == 1, srch["total"])

print("\n== sessions never hold out-of-scope hosts ==")
s, sess = call("GET", f"/connectors/{cid}/sessions?project_id={PID}")
hosts = {h for row in sess for h in row["hosts"]}
check("the tested host is present", HOST in hosts, hosts)

print("\n== only-known-hosts discards, and says so ==")
call("PATCH", f"/connectors/{cid}?project_id={PID}", {"only_known_hosts": True})
s, strict = call(
    "POST",
    "/connectors/ingest",
    {
        "client": "e2e",
        "items": [
            {
                "url": "https://private.example-notmine-rengine.com/x",
                "method": "GET",
                "status_code": 200,
                "source_tool": "proxy",
            }
        ],
    },
    token=secret,
)
check(
    "an unknown host is discarded when asked",
    strict["dropped"] == 1 and strict["accepted"] == 0,
    strict,
)
s, after_strict = call(
    "GET", f"/connectors/{cid}/candidates?project_id={PID}&search=example-notmine"
)
check(
    "nothing about it is stored", (after_strict or {}).get("total") == 0, after_strict
)
call("PATCH", f"/connectors/{cid}?project_id={PID}", {"only_known_hosts": False})

print("\n== pause ==")
call("PATCH", f"/connectors/{cid}?project_id={PID}", {"paused": True})
s, rp = call(
    "POST",
    "/connectors/ingest",
    {
        "items": [
            {
                "url": f"https://{HOST}/paused-probe",
                "method": "GET",
                "source_tool": "proxy",
            }
        ]
    },
    token=secret,
)
check("paused connector stores nothing", rp["accepted"] == 0 and rp["novel"] == 0, rp)
call("PATCH", f"/connectors/{cid}?project_id={PID}", {"paused": False})

print("\n== state changes ==")
ids = [r["id"] for r in page["rows"][:1]]
s, ch = call(
    "POST",
    f"/connectors/{cid}/candidates/state?project_id={PID}",
    {"ids": ids, "state": "ignored"},
)
check("state change applied", ch["changed"] == 1, ch)
s, _ = call(
    "POST",
    f"/connectors/{cid}/candidates/state?project_id={PID}",
    {"ids": ids, "state": "bogus"},
)
check("unknown state rejected", s == BAD_REQUEST, s)
call(
    "POST",
    f"/connectors/{cid}/candidates/state?project_id={PID}",
    {"ids": ids, "state": "new"},
)

print("\n== discovered domains ==")
UNKNOWN = "e2e-partner-check-rengine.com"
call(
    "POST",
    "/connectors/ingest",
    {
        "client": "e2e",
        "items": [
            {
                "url": f"https://portal.{UNKNOWN}/login",
                "method": "GET",
                "status_code": 200,
                "source_tool": "proxy",
            },
            {
                "url": f"https://api.{UNKNOWN}/v1/ping",
                "method": "GET",
                "status_code": 200,
                "source_tool": "proxy",
            },
            {
                "url": "https://ad.doubleclick.net/beacon",
                "method": "GET",
                "status_code": 200,
                "source_tool": "proxy",
            },
            {
                "url": "https://analytics.google.com/g/collect",
                "method": "POST",
                "status_code": 204,
                "source_tool": "proxy",
            },
        ],
    },
    token=secret,
)
s, found = call("GET", f"/connectors/{cid}/discovered?project_id={PID}")
domains = {d["domain"]: d for d in (found or [])}
check("an unknown domain is offered", UNKNOWN in domains, sorted(domains))
check(
    "ad and analytics domains are not offered",
    "doubleclick.net" not in domains and "google.com" not in domains,
    sorted(domains),
)
check(
    "the offer groups its hostnames",
    domains.get(UNKNOWN, {}).get("hostname_count") == FOLDED_SHAPES,
    domains.get(UNKNOWN),
)
check(
    "the offer carries a reason",
    domains.get(UNKNOWN, {}).get("reason") == "proxy_traffic",
)

s, addition = call(
    "POST", f"/connectors/{cid}/discovered/add?project_id={PID}", {"domain": UNKNOWN}
)
check("adding it creates a target", s == OK and addition.get("target_id"), addition)
new_target = (addition or {}).get("target_id")
s, after_add = call("GET", f"/connectors/{cid}/discovered?project_id={PID}")
check(
    "it stops being offered once added",
    UNKNOWN not in {d["domain"] for d in (after_add or [])},
    after_add,
)
s, tget = call("GET", f"/targets/{new_target}?project_id={PID}")
check("the target really exists", s == OK and tget.get("target_value") == UNKNOWN, tget)

print("\n== add-as-target does not over-claim ==")
NEIGHBOUR = f"not{UNKNOWN}"

call(
    "POST",
    "/connectors/ingest",
    {
        "client": "e2e",
        "items": [
            {
                "url": f"https://{NEIGHBOUR}/x",
                "method": "GET",
                "status_code": 200,
                "source_tool": "proxy",
            },
            {
                "url": f"https://real.{UNKNOWN}/x",
                "method": "GET",
                "status_code": 200,
                "source_tool": "proxy",
            },
        ],
    },
    token=secret,
)

call("POST", f"/connectors/{cid}/discovered/add?project_id={PID}", {"domain": UNKNOWN})
s, near = call("GET", f"/connectors/{cid}/candidates?project_id={PID}&search=/x")
by_host = {r["host"]: r for r in (near or {}).get("rows", [])}
check(
    "a real subdomain is claimed by the added target",
    (by_host.get(f"real.{UNKNOWN}") or {}).get("target_id") is not None,
    sorted(by_host),
)
check(
    "a lookalike host is stored but not claimed",
    NEIGHBOUR in by_host and by_host[NEIGHBOUR].get("target_id") is None,
    by_host.get(NEIGHBOUR, "row missing"),
)

print("\n== hosts serving only assets are still discovered ==")
ASSET_ONLY = "e2e-assets-only-rengine.com"
call(
    "POST",
    "/connectors/ingest",
    {
        "client": "e2e",
        "items": [
            {
                "url": f"https://cdn.{ASSET_ONLY}/app.js",
                "method": "GET",
                "status_code": 200,
                "content_type": "application/javascript",
                "source_tool": "proxy",
            }
        ],
    },
    token=secret,
)
s, assets = call("GET", f"/connectors/{cid}/discovered?project_id={PID}")
check(
    "a host that only served assets is still offered",
    ASSET_ONLY in {d["domain"] for d in (assets or [])},
    assets,
)

print("\n== dismiss ==")
call(
    "POST",
    "/connectors/ingest",
    {
        "client": "e2e",
        "items": [
            {
                "url": "https://portal.e2e-dismiss-check-rengine.com/x",
                "method": "GET",
                "status_code": 200,
                "source_tool": "proxy",
            }
        ],
    },
    token=secret,
)
s, dis = call(
    "POST",
    f"/connectors/{cid}/discovered/dismiss?project_id={PID}",
    {"domain": "e2e-dismiss-check-rengine.com"},
)
check("dismiss marks the hosts", s == OK and dis.get("dismissed", 0) >= 1, dis)
s, left = call("GET", f"/connectors/{cid}/discovered?project_id={PID}")
check(
    "a dismissed domain is not offered again",
    "e2e-dismiss-check-rengine.com" not in {d["domain"] for d in (left or [])},
    left,
)

print("\n== reNgine hands the proxy what it knows ==")
s, options = call("GET", "/connectors/targets", token=secret)
check("the picker lists targets", s == OK and len(options or []) >= 1, options)
picked_target = next((t for t in (options or []) if t["value"] == HOST), None)
check(
    "the tested target is offered",
    picked_target is not None,
    [t["value"] for t in (options or [])],
)
check(
    "it reports whether a scan has covered it",
    isinstance((picked_target or {}).get("endpoints"), int),
    picked_target,
)

s, scope = call(
    "GET", f"/connectors/scope?target_id={picked_target['id']}", token=secret
)
check("scope rules are returned", s == OK and scope.get("target_value") == HOST, scope)
check(
    "every rule is a URL the proxy can apply",
    all(r.startswith("https://") for r in scope["include"] + scope["exclude"]),
    scope["include"][:3],
)
check(
    "the target itself is in scope",
    f"https://{HOST}" in scope["include"],
    scope["include"][:3],
)
s, _ = call(
    "GET",
    "/connectors/scope?target_id=00000000-0000-0000-0000-000000000000",
    token=secret,
)
check("a target outside the project is refused", s == BAD_REQUEST, s)

s, facts = call("GET", f"/connectors/host?host={HOST}", token=secret)
check("host facts are returned", s == OK and facts.get("host") == HOST, facts)
check("facts name the target", facts.get("target_value") == HOST, facts)
check(
    "reached never exceeds known", facts["visited"] <= facts["known_endpoints"], facts
)
s, unknown = call(
    "GET", "/connectors/host?host=nothing-here-rengine.test", token=secret
)
check(
    "an unknown host reports zero, not an error",
    s == OK and unknown["known_endpoints"] == 0 and unknown["target_value"] is None,
    unknown,
)

print("\n== a bug bounty program's scope ==")
s, picker = call("GET", "/connectors/targets", token=secret)
programs = [o for o in (picker or []) if o["kind"] == "program"]
if programs:
    program = programs[0]
    check("the picker offers the program", program["targets"] >= 1, program)
    s, pscope = call(
        "GET", f"/connectors/scope?program_id={program['id']}", token=secret
    )
    check(
        "its scope comes from the program's own rules",
        s == OK and pscope["from_scope_rules"] is True,
        pscope,
    )
    check(
        "out-of-scope assets become exclusions",
        len(pscope["exclude"]) >= 1,
        pscope["exclude"][:3],
    )

    s, _ = call(
        "GET",
        f"/connectors/scope?target_id={program['id']}&program_id={program['id']}",
        token=secret,
    )
    check("giving both a target and a program is refused", s == BAD_REQUEST, s)

    forbidden = pscope["exclude"][0].removeprefix("https://")
    s, warned = call(
        "POST",
        "/connectors/ingest",
        {
            "client": "e2e",
            "items": [
                {
                    "url": f"https://{forbidden}/login",
                    "method": "GET",
                    "status_code": 200,
                    "source_tool": "proxy",
                }
            ],
        },
        token=secret,
    )
    check(
        "browsing an out-of-scope host is flagged",
        any("out_of_scope" in f["notices"] for f in warned["flagged"]),
        warned["flagged"],
    )
    s, _ = call(
        "POST",
        f"/connectors/{cid}/discovered/add?project_id={PID}",
        {"domain": forbidden},
    )
    check("it cannot be added as a target", s == BAD_REQUEST, s)
else:
    print("     (no bounty program resolves to a target in this project; skipped)")

print("\n== reNgine speaks while the tester works ==")
call(
    "POST",
    "/connectors/ingest",
    {
        "client": "e2e",
        "items": [
            {
                "url": f"https://{HOST}/.env",
                "method": "GET",
                "status_code": 200,
                "source_tool": "proxy",
            },
            {
                "url": f"https://{HOST}/quiet-page",
                "method": "GET",
                "status_code": 200,
                "source_tool": "proxy",
            },
        ],
    },
    token=secret,
)
s, said = call("GET", "/connectors/notices", token=secret)
check("loud findings are handed to the proxy", s == OK and len(said or []) >= 1, said)
check(
    "every notice carries a label and a url",
    all(n.get("label") and n.get("url") for n in (said or [])),
    said,
)
check(
    "a quiet page is not announced",
    all("quiet-page" not in n["url"] for n in (said or [])),
    said,
)
s, again3 = call("GET", "/connectors/notices", token=secret)
check("a notice is delivered once", again3 == [], again3)

print("\n== the tester reports what they found ==")
s, recorded = call(
    "POST",
    "/connectors/findings",
    {
        "title": "IDOR on the order endpoint",
        "url": f"https://{HOST}/api/v9/orders/4242",
        "severity": "high",
        "method": "GET",
        "notes": "Changing the id returns another customer.",
        "request": "GET /api/v9/orders/4242 HTTP/1.1",
        "response": "HTTP/1.1 200 OK",
    },
    token=secret,
)
check("the finding is recorded", s == OK and recorded.get("finding_id"), recorded)
check("it belongs to the tested target", recorded.get("target_value") == HOST, recorded)
manual_scan = recorded.get("scan_id")
s, twice = call(
    "POST",
    "/connectors/findings",
    {
        "title": "IDOR on the order endpoint",
        "url": f"https://{HOST}/api/v9/orders/4242",
        "severity": "high",
    },
    token=secret,
)
check(
    "reporting it twice is one finding",
    twice.get("total") == recorded.get("total"),
    twice,
)
s, bad = call(
    "POST",
    "/connectors/findings",
    {"title": "x", "url": "https://not-a-target-rengine.test/a", "severity": "high"},
    token=secret,
)
check("a host with no target is refused", s == BAD_REQUEST, s)
s, wrong = call(
    "POST",
    "/connectors/findings",
    {"title": "x", "url": f"https://{HOST}/a", "severity": "catastrophic"},
    token=secret,
)
check("an unknown severity is refused", s == BAD_REQUEST, s)

s, found = call(
    "POST",
    f"/vulnerabilities/search?project_id={PID}&scan_id={manual_scan}",
    {"q": "scanner:manual"},
)
rows = (found or {}).get("items", [])
check("it is queryable through the normal grammar", len(rows) >= 1, found)
check(
    "it carries its own provenance",
    rows and rows[0]["scanner"] == "manual",
    rows[0] if rows else None,
)

print("\n== send back to the proxy ==")
s, queue_page = call("GET", f"/connectors/{cid}/candidates?project_id={PID}&state=new")
pick = [r["id"] for r in (queue_page or {}).get("rows", [])[:2]]
s, queued = call(
    "POST",
    f"/connectors/{cid}/send?project_id={PID}",
    {"ids": pick, "kind": "repeater"},
)
check(
    "shapes are queued for the proxy",
    s == OK and queued.get("queued") == len(pick),
    queued,
)

s, listed = call("GET", f"/connectors?project_id={PID}")
mine = next((c for c in listed if c["id"] == cid), {})
check(
    "the connector reports work waiting",
    mine.get("pending_actions") == len(pick),
    mine.get("pending_actions"),
)

s, _ = call(
    "POST", f"/connectors/{cid}/send?project_id={PID}", {"ids": [], "kind": "repeater"}
)
check("an empty selection is refused", s == BAD_REQUEST, s)
s, _ = call(
    "POST", f"/connectors/{cid}/send?project_id={PID}", {"ids": pick, "kind": "nope"}
)
check("an unknown action is refused", s == BAD_REQUEST, s)

s, collected = call("GET", "/connectors/actions", token=secret)
check(
    "the proxy collects them", s == OK and len(collected or []) == len(pick), collected
)
check(
    "each carries a url and a method",
    all(a.get("url") and a.get("method") for a in (collected or [])),
    collected,
)
s, again2 = call("GET", "/connectors/actions", token=secret)
check("an action is delivered once, never replayed", again2 == [], again2)
s, _ = call("GET", "/connectors/actions", token="rngconn_" + "0" * 48)
check("collecting needs a valid token", s == UNAUTHORIZED, s)

print("\n== scan dispatch ==")
s, scan = call("POST", f"/connectors/{cid}/scan?project_id={PID}", {"ids": []})
check("scan launched", s == OK and scan.get("id"), scan)
sid = scan["id"]
check("run is focused", scan.get("scope") == "focused", scan.get("scope"))
s, after = call("GET", f"/connectors/{cid}/candidates?project_id={PID}&state=queued")
check("candidates moved to queued", after["total"] >= 1, after["total"])
check("queued rows carry the scan id", all(r["scan_id"] == sid for r in after["rows"]))

print("\n== isolation ==")
s, _ = call(
    "GET",
    f"/connectors/{cid}/candidates?project_id=00000000-0000-0000-0000-000000000000",
)
check("wrong project is a 404", s == NOT_FOUND, s)

print("\n== token rotation ==")
s, rot = call("POST", f"/connectors/{cid}/rotate?project_id={PID}")
new_secret = rot["secret"]
check("rotate returns a new secret", s == OK and new_secret != secret)
s, _ = call("POST", "/connectors/ingest", {"items": []}, token=secret)
check("old token no longer works", s == UNAUTHORIZED, s)
s, _ = call("POST", "/connectors/ingest", {"items": []}, token=new_secret)
check("new token works", s == OK, s)

print("\n== delete cascades ==")
s, _ = call("DELETE", f"/connectors/{cid}?project_id={PID}", raw=True)
check("delete returns 204", s == NO_CONTENT, s)
s, _ = call("GET", f"/connectors/{cid}/candidates?project_id={PID}")
check("connector is gone", s == NOT_FOUND, s)
s, _ = call("POST", "/connectors/ingest", {"items": []}, token=new_secret)
check("token dies with the connector", s == UNAUTHORIZED, s)

print("\n== a token cannot be guessed at speed ==")
codes = []
for attempt in range(TOKEN_ATTEMPTS):
    status_code, _ = call(
        "POST",
        "/connectors/ingest",
        {"items": []},
        token="rngconn_" + f"{attempt:048d}",
    )
    codes.append(status_code)
check("wrong tokens are refused", codes[0] == UNAUTHORIZED, codes[0])
check(
    "guessing is throttled before the window closes",
    TOO_MANY in codes,
    sorted(set(codes)),
)

if new_target:
    call("DELETE", f"/targets/{new_target}?project_id={PID}")

print(f"\n{len(passed)} passed, {len(failed)} failed")
if failed:
    print("FAILED:", *failed, sep="\n  - ")
sys.exit(1 if failed else 0)
