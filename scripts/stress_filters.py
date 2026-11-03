"""Regression stress for the filter grammar behind suggestions and chips, against a running api.

Usage: RENGINE_USER=… RENGINE_PASSWORD=… python scripts/stress_filters.py <project id> [scan id|-]
BURST=<workers> adds a concurrent burst of count calls.
"""

import http.cookiejar
import itertools
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = os.environ.get("RENGINE_URL", "http://127.0.0.1:5173")
OK = 200
MAX_PAIRS = int(os.environ.get("MAX_PAIRS", "400"))
SLOW_MS = 3000
COUNT_BATCH = 32
BURST_ROUNDS = 6
P95 = 0.95
LEADS_ROUTES = {"subdomains", "ports", "ips", "vulnerabilities", "endpoints"}
NUMERIC = {"ports", "asns"}
DIMENSIONS: dict[str, tuple[list[str], dict[str, str], bool]] = {
    "subdomains": (
        ["web_assets", "hosts", "subdomains"],
        {
            "status": "statuses",
            "tech": "tech",
            "service": "services",
            "source": "sources",
            "cert": "cert",
            "hygiene": "hygiene",
            "posture": "posture",
        },
        False,
    ),
    "ports": (
        ["services", "ports"],
        {
            "class": "classes",
            "port": "ports",
            "service": "services",
            "source": "sources",
            "asn": "asns",
            "country": "countries",
        },
        False,
    ),
    "ips": (
        ["ips", "ip_addresses", "addresses"],
        {
            "exposure": "exposure",
            "asn": "asns",
            "country": "countries",
            "port": "ports",
            "service": "services",
        },
        False,
    ),
    "vulnerabilities": (
        ["vulnerabilities", "findings"],
        {
            "severity": "severities",
            "state": "states",
            "protocol": "protocols",
            "template": "templates",
            "tag": "tags",
            "host": "hosts",
            "scanner": "scanners",
        },
        False,
    ),
    "endpoints": (
        ["endpoints"],
        {
            "endpoint_class": "endpoint_class",
            "source": "source",
            "interest": "interest",
            "status_class": "status_class",
        },
        True,
    ),
    "software": (["software"], {}, False),
    "secrets": (["secrets"], {}, False),
}


class Api:
    def __init__(self, project: str, scan: str | None) -> None:
        self.project = project
        self.scan = scan
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(jar)
        )
        self.latencies: dict[str, list[float]] = {}
        self.failures: list[str] = []

    def call(
        self, method: str, path: str, body: dict | None = None
    ) -> tuple[int, dict]:
        query = {
            "project_id": self.project,
            **({"scan_id": self.scan} if self.scan else {}),
        }
        url = f"{BASE}/api/v1{path}?" + "&".join(f"{k}={v}" for k, v in query.items())
        data = json.dumps(body).encode() if body is not None else None
        headers = {"content-type": "application/json"}
        req = urllib.request.Request(url, data=data, method=method, headers=headers)  # noqa: S310
        t0 = time.perf_counter()
        try:
            with self.opener.open(req, timeout=60) as r:
                payload = json.loads(r.read() or b"null")
                status = r.status
        except urllib.error.HTTPError as e:
            payload = json.loads(e.read() or b"null")
            status = e.code
        ms = (time.perf_counter() - t0) * 1000
        self.latencies.setdefault(path, []).append(ms)
        if ms > SLOW_MS:
            self.failures.append(
                f"slow {ms:.0f} ms {method} {path} {json.dumps(body)[:80] if body else ''}"
            )
        return status, payload if isinstance(payload, dict) else {"value": payload}

    def check(self, cond: bool, message: str) -> bool:
        if not cond:
            self.failures.append(message)
        return cond

    def login(self) -> None:
        body = {
            "username": os.environ["RENGINE_USER"],
            "password": os.environ["RENGINE_PASSWORD"],
        }
        status, _ = self.call("POST", "/auth/login", body)
        if status != OK:
            message = f"login {status}"
            raise SystemExit(message)

    def counts(self, dim: str, queries: list[str]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for start in range(0, len(queries), COUNT_BATCH):
            batch = queries[start : start + COUNT_BATCH]
            status, res = self.call("POST", f"/{dim}/search/counts", {"queries": batch})
            self.check(
                status == OK and bool(res.get("computed")),
                f"{dim}: counts {status} {str(res)[:160]}",
            )
            counts.update(res.get("counts", {}))
        return counts


def coerce(field: str, value: object) -> object:
    if field not in NUMERIC:
        return value
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def clause(query: str) -> str:
    return f"({query})" if " or " in query else query


def stress_queries(
    api: Api, dim: str, queries: list[str], leads: dict[str, int], total: int | None
) -> tuple[dict[str, int], int]:
    counts = api.counts(dim, queries)
    for q in queries:
        api.check(q in counts, f"{dim}: {q!r} did not compile in counts")
        if q in leads and q in counts:
            api.check(
                leads[q] == counts[q],
                f"{dim}: lead {q!r} counts {leads[q]} vs counts endpoint {counts[q]}",
            )
        if total is not None and q in counts:
            api.check(
                counts[q] <= total,
                f"{dim}: {q!r} count {counts[q]} above total {total}",
            )
    live = [q for q in queries if counts.get(q, 0) > 0]
    for q in live:
        body: dict[str, object] = {"q": q}
        body.update(
            {"page": 1, "size": 1} if dim == "endpoints" else {"limit": 1, "offset": 0}
        )
        status, res = api.call("POST", f"/{dim}/search", body)
        if api.check(
            status == OK and not res.get("error"),
            f"{dim}: search {q!r} -> {status} {str(res.get('error') or res)[:120]}",
        ):
            api.check(
                res.get("total") == counts[q],
                f"{dim}: {q!r} search total {res.get('total')} differs from count {counts[q]}",
            )
    pairs = list(itertools.combinations(live, 2))[:MAX_PAIRS]
    joined = {f"{clause(a)} and {clause(b)}": (a, b) for a, b in pairs}
    pair_counts = api.counts(dim, list(joined)) if joined else {}
    for j, (a, b) in joined.items():
        if not api.check(j in pair_counts, f"{dim}: {j!r} did not compile"):
            continue
        n = pair_counts[j]
        api.check(
            n <= min(counts[a], counts[b]),
            f"{dim}: {j!r} = {n} exceeds its parts {counts[a]}/{counts[b]}",
        )
    return counts, len(joined)


def stress_facets(
    api: Api,
    dim: str,
    facet_map: dict[str, str],
    single: bool,
    live: list[str],
    counts: dict[str, int],
) -> int:
    status, facets = api.call("GET", f"/{dim}/facets")
    if status != OK:
        return 0
    checks = 0
    for key, field in facet_map.items():
        for option in (facets.get(key) or [])[:2]:
            raw = option.get("value", option.get("name"))
            value = coerce(field, raw)
            if value is None:
                continue
            for q in live[:3]:
                body: dict[str, object] = {"q": q, field: value if single else [value]}
                body.update(
                    {"page": 1, "size": 5}
                    if dim == "endpoints"
                    else {"limit": 5, "offset": 0}
                )
                status, res = api.call("POST", f"/{dim}/search", body)
                checks += 1
                ok = api.check(
                    status == OK and not res.get("error"),
                    f"{dim}: search {key}={raw!r} + {q!r} -> {status} {str(res.get('error') or res)[:120]}",
                )
                if ok and "total" in res:
                    api.check(
                        res["total"] <= counts[q],
                        f"{dim}: {key}={raw!r} + {q!r} total {res['total']} above {counts[q]}",
                    )
    return checks


def stress_tabs(api: Api, dim: str, live: list[str]) -> int:
    if dim not in LEADS_ROUTES:
        return 0
    for q in live[:12]:
        status, res = api.call("POST", f"/{dim}/search/tabs", {"q": q})
        api.check(
            status == OK and res.get("computed", True),
            f"{dim}: tabs under {q!r} -> {status} {str(res)[:120]}",
        )
    return min(len(live), 12)


def stress_dimension(
    api: Api, dim: str, schemas: dict
) -> tuple[str, int, int, int, str]:
    schema_keys, facet_map, single = DIMENSIONS[dim]
    examples = next(
        (
            [e["query"] for e in schemas[k].get("examples", [])]
            for k in schema_keys
            if k in schemas
        ),
        [],
    )
    leads: dict[str, int] = {}
    total: int | None = None
    if dim in LEADS_ROUTES:
        status, res = api.call("POST", f"/{dim}/search/leads", {})
        api.check(
            status == OK and bool(res.get("computed")),
            f"{dim}: leads {status} {str(res)[:120]}",
        )
        leads = {lead["query"]: lead["count"] for lead in res.get("leads", [])}
        total = res.get("total")
    queries = list(dict.fromkeys([*leads, *examples]))
    if not queries:
        return dim, 0, 0, 0, "no queries"
    counts, pairs = stress_queries(api, dim, queries, leads, total)
    live = [q for q in queries if counts.get(q, 0) > 0]
    checks = stress_facets(api, dim, facet_map, single, live, counts) + stress_tabs(
        api, dim, live
    )
    return (
        dim,
        len(queries),
        pairs,
        checks,
        f"total {total}" if total is not None else "",
    )


def burst(api: Api, workers: int) -> None:
    dim = "subdomains"
    _, res = api.call("POST", f"/{dim}/search/leads", {})
    live = [lead["query"] for lead in res.get("leads", []) if lead["count"] > 0][
        :COUNT_BATCH
    ]
    if not live:
        return

    def one(_: int) -> bool:
        status, r = api.call("POST", f"/{dim}/search/counts", {"queries": live})
        return status == OK and bool(r.get("computed"))

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = list(pool.map(one, range(workers * BURST_ROUNDS)))
    wall = time.perf_counter() - t0
    api.check(
        all(outcomes),
        f"burst: {outcomes.count(False)} of {len(outcomes)} count calls failed",
    )
    print(
        f"burst: {len(outcomes)} count calls, {workers} at a time, {len(live)} queries each, {wall:.1f} s wall"
    )


def report(api: Api, rows: list[tuple[str, int, int, int, str]]) -> None:
    print()
    print(f"{'dimension':16} {'queries':>8} {'pairs':>6} {'facet+tab':>10}  note")
    for dim, nq, npairs, nf, note in rows:
        print(f"{dim:16} {nq:8} {npairs:6} {nf:10}  {note}")
    print()
    print(f"{'route':40} {'calls':>6} {'p50 ms':>8} {'p95 ms':>8} {'max ms':>8}")
    for path, ms in sorted(api.latencies.items()):
        ms.sort()
        p95 = ms[min(len(ms) - 1, int(len(ms) * P95))]
        print(
            f"{path:40} {len(ms):6} {statistics.median(ms):8.0f} {p95:8.0f} {ms[-1]:8.0f}"
        )
    print()
    if api.failures:
        print(f"{len(api.failures)} failures")
        for failure in api.failures[:60]:
            print(" -", failure)
        raise SystemExit(1)
    print("0 failures")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    project = args[0]
    scan = args[1] if len(args) > 1 and args[1] != "-" else None
    api = Api(project, scan)
    api.login()
    status, schemas = api.call("GET", "/surface/schemas")
    if status != OK:
        message = f"schemas {status}"
        raise SystemExit(message)
    print("schemas:", list(schemas))
    rows = [stress_dimension(api, dim, schemas) for dim in DIMENSIONS]
    if os.environ.get("BURST"):
        burst(api, int(os.environ["BURST"]))
    report(api, rows)


main()
