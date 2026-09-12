#!/usr/bin/env python3
"""Walk the connector workflow as a pentester would, reporting what they would see."""

import http.cookiejar
import json
import os
import secrets
import urllib.error
import urllib.request

BASE = "http://localhost:8000/api/v1"
PID = os.environ.get("RENGINE_PROJECT_ID", "")
USER = os.environ.get("RENGINE_USER", "rengine")
PASSWORD = os.environ.get("RENGINE_PASSWORD", "rengine@123")
if not PID:
    print("Set RENGINE_PROJECT_ID to the project to walk.")
    raise SystemExit(2)
OK = 200
SITE = f"journey-{secrets.token_hex(3)}-rengine.com"
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def call(method, path, body=None, token=None):
    req = urllib.request.Request(  # noqa: S310
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
    )
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with opener.open(req) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, None


def step(n, text):
    print(f"\n{n}. {text}")


def saw(text):
    print(f"     → {text}")


def friction(text):
    print(f"     !! {text}")


call("POST", "/auth/login", {"username": USER, "password": PASSWORD})

step(1, "Pentester creates a connector. It asks for a name and a proxy, nothing else.")
s, made = call(
    "POST", "/connectors", {"name": "My Burp", "kind": "burp", "project_id": PID}
)
tok = made["secret"]
cid = made["connector"]["id"]
saw(
    f"token issued, {len(made['setup']['steps'])} setup steps, endpoint {made['setup']['endpoint']}"
)

step(2, "Loads the jar, pastes the token, presses Test connection.")
s, _ = call(
    "POST", "/connectors/ingest", {"client": "burp/2026.4.2", "items": []}, token=tok
)
saw(f"connection test -> HTTP {s}")

step(3, "Opens the Working on picker before knowing what they'll test.")
s, options = call("GET", "/connectors/targets", token=tok)
if not isinstance(options, list):
    friction(f"the picker could not be read (HTTP {s})")
    options = []
saw(f"{len(options)} offered: {[o['value'] for o in options][:4]}")
if not any(o["value"] == SITE for o in options):
    saw(
        f"{SITE} is NOT there — it is not a target yet. Picker stays on Match by hostname."
    )

step(4, "Starts testing a site that is not a target. Browses for a while.")
batch = {
    "client": "burp/2026.4.2",
    "items": [
        {
            "url": f"https://www.{SITE}/",
            "method": "GET",
            "status_code": 200,
            "content_type": "text/html",
            "title": "Shop",
            "source_tool": "proxy",
        },
        {
            "url": f"https://www.{SITE}/admin/",
            "method": "GET",
            "status_code": 200,
            "source_tool": "proxy",
        },
        {
            "url": f"https://www.{SITE}/api/orders/1201",
            "method": "GET",
            "status_code": 200,
            "authenticated": True,
            "source_tool": "proxy",
        },
        {
            "url": f"https://www.{SITE}/api/orders/1202",
            "method": "GET",
            "status_code": 200,
            "authenticated": True,
            "source_tool": "proxy",
        },
        {
            "url": f"https://checkout.{SITE}/pay",
            "method": "POST",
            "status_code": 500,
            "authenticated": True,
            "source_tool": "proxy",
            "body_params": ["card", "cvv"],
        },
        {
            "url": "https://www.googletagmanager.com/gtm.js",
            "method": "GET",
            "status_code": 200,
            "source_tool": "proxy",
        },
    ],
}
s, r = call("POST", "/connectors/ingest", batch, token=tok)
saw(
    f"accepted {r['accepted']}, dropped {r['dropped']}, flagged {[f['url'].split('/')[-2] or '/' for f in r['flagged']]}"
)

step(5, "Switches to reNgine. What is on the Queue?")
s, q = call("GET", f"/connectors/{cid}/candidates?project_id={PID}")
for row in q["rows"]:
    saw(f"{row['methods']!s:9} {row['host']}{row['path']:24} {row['notices']}")
s, listed = call("GET", f"/connectors?project_id={PID}")
me = next(c for c in listed if c["id"] == cid)
saw(
    f"stats: {me['candidates']} shapes · {me['unassigned']} unassigned · {me['discovered']} domains to look at"
)
if me["unassigned"] == me["candidates"]:
    saw("everything is unassigned, because no target matches yet")

step(6, "Opens Discovered. Is the site offered?")
s, disc = call("GET", f"/connectors/{cid}/discovered?project_id={PID}")
for d in disc:
    saw(
        f"{d['domain']} · {d['hostname_count']} host(s) · {d['requests']} requests · {d['reason_label']}"
    )
if not any(d["domain"] == SITE for d in disc):
    friction(f"{SITE} is not offered")

step(7, "Presses Add and scan, because reNgine knows nothing about this site yet.")
s, added = call(
    "POST",
    f"/connectors/{cid}/discovered/add?project_id={PID}",
    {"domain": SITE, "scan": True},
)
saw(
    f"HTTP {s} · target created · {added.get('attached')} recorded rows attached · scan {str(added.get('scan_id'))[:8]}"
)

step(8, "Does the browsing done BEFORE adding attach retroactively?")
s, q2 = call("GET", f"/connectors/{cid}/candidates?project_id={PID}")
mine = [r for r in q2["rows"] if r["host"].endswith(SITE)]
attached = [r for r in mine if r["target_id"]]
saw(f"{len(attached)} of {len(mine)} rows under the site now belong to the target")
if len(attached) != len(mine):
    friction("some earlier browsing did not attach")

step(9, "Back in Burp, reloads the picker. Is it there now?")
s, options2 = call("GET", "/connectors/targets", token=tok)
match = next((o for o in options2 if o["value"] == SITE), None)
saw(
    f"offered: {match['value'] if match else 'NO'} · {match['endpoints'] if match else 0} endpoints scanned"
)

step(10, "Presses Apply scope to Burp.")
s, scope = call("GET", f"/connectors/scope?target_id={added['target_id']}", token=tok)
saw(f"HTTP {s}, {len(scope['include'])} include rules: {scope['include'][:3]}")
if len(scope["include"]) <= 1:
    friction(
        "scope is only the bare target — reNgine has not scanned it, so it knows no hostnames"
    )

step(11, "What does the tab say about the host being tested?")
s, facts = call("GET", f"/connectors/host?host=www.{SITE}", token=tok)
saw(
    f"{facts['host']} · {facts['known_endpoints']} known · {facts['visited']} reached · target {facts['target_value']}"
)
if facts["known_endpoints"] == 0:
    friction("no scan has covered it, so coverage has nothing to say yet")

step(12, "Opens the target's Endpoints page. Is the browsing there?")
s, eps = call(
    "POST",
    f"/endpoints/search?project_id={PID}",
    {"q": "source:proxy", "host": None, "page": 1, "size": 50},
)
rows = (eps or {}).get("items") or (eps or {}).get("rows") or []
saw(f"{len(rows)} endpoints carry source:proxy: {[r['path'] for r in rows][:6]}")
if not rows:
    friction("browsing did not land in the Endpoints inventory")

step(13, "Sends the interesting ones to Repeater.")
picks = [
    r["id"]
    for r in q2["rows"]
    if "admin" in r["path"] or "server_error" in r["notices"]
]
s, sent = call(
    "POST",
    f"/connectors/{cid}/send?project_id={PID}",
    {"ids": picks, "kind": "repeater"},
)
saw(f"queued {sent.get('queued')} for Burp to collect")
s, collected = call("GET", "/connectors/actions", token=tok)
saw(f"Burp collected {len(collected)}: {[a['label'] for a in collected]}")

step(14, "Scans the rest.")
s, scans = call("POST", f"/connectors/{cid}/scan?project_id={PID}", {"ids": []})
scan = (scans or [{}])[0] if isinstance(scans, list) else (scans or {})
saw(f"HTTP {s} · {scan.get('engine_name') if s == OK else scans}")

print("\n--- cleanup ---")
for run in (scan.get("id"), added.get("scan_id")):
    if run:
        code, _ = call("POST", f"/scans/{run}/cancel?project_id={PID}")
        print(f"     cancel scan -> {code}")
call("DELETE", f"/connectors/{cid}?project_id={PID}")
if added.get("target_id"):
    code, _ = call("DELETE", f"/targets/{added['target_id']}?project_id={PID}")
    print(f"     delete target -> {code}")
print("done")
