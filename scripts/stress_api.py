"""Load a running api with the request mix of one page profile and report latency per route.

Usage: stress_api.py PROJECT_ID --profile dashboard --concurrency 8 --duration 60 --target-id ID
Credentials: RENGINE_USER and RENGINE_PASSWORD, or RENGINE_ACCOUNTS naming a file of user:password lines.
"""

import argparse
import http.client
import http.cookiejar
import json
import os
import random
import re
import statistics
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

OK = 200
SERVER_ERROR = 500
THROTTLED = 429
TIMEOUT = 60
SSE_ROUTE = "SSE handshake"
COUNT_BATCH = 32
MAX_CONCURRENCY = 16
DEAD_LIMIT = 20
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
PROFILES = ("dashboard", "cells", "target", "scan", "surface", "search-typing", "mixed")
MIXED_WEIGHTS = {
    "dashboard": 3,
    "target": 2,
    "scan": 3,
    "surface": 1,
    "search-typing": 2,
}
LEAD_DIMS = ("subdomains", "ports", "ips", "vulnerabilities", "endpoints")
TYPED = ["host:" + "stress-agency-0123.gov.cy"[:n] for n in range(6, 20)] + [
    "tech:" + "nginx"[:n] for n in range(1, 6)
]

Request = tuple[str, str, dict | None]


class Session:
    def __init__(self, base: str, user: str, password: str) -> None:
        self.base = base
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )
        status, body, _ = self.send(
            "POST", "/auth/login", {"username": user, "password": password}
        )
        if status != OK:
            message = f"login {status} {body[:120]!r}"
            raise SystemExit(message)

    def send(
        self, method: str, path: str, body: dict | None = None
    ) -> tuple[int, bytes, float]:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(  # noqa: S310
            f"{self.base}/api/v1{path}",
            data=data,
            method=method,
            headers={"content-type": "application/json"},
        )
        t0 = time.perf_counter()
        try:
            with self.opener.open(req, timeout=TIMEOUT) as r:
                payload = r.read()
                status = r.status
        except urllib.error.HTTPError as e:
            payload = e.read()
            status = e.code
        except (OSError, http.client.HTTPException):
            payload = b""
            status = 0
        return status, payload, (time.perf_counter() - t0) * 1000

    def handshake(self, path: str) -> tuple[int, float]:
        req = urllib.request.Request(f"{self.base}/api/v1{path}")  # noqa: S310
        t0 = time.perf_counter()
        try:
            r = self.opener.open(req, timeout=TIMEOUT)
            status = r.status
            r.close()
        except urllib.error.HTTPError as e:
            status = e.code
        except (OSError, http.client.HTTPException):
            status = 0
        return status, (time.perf_counter() - t0) * 1000


class Stats:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.ms: dict[str, list[float]] = {}
        self.status: dict[str, dict[int, int]] = {}
        self.samples: dict[str, str] = {}
        self.dead = 0
        self.stopped = threading.Event()

    def add(self, route: str, status: int, ms: float, body: bytes = b"") -> None:
        with self.lock:
            self.ms.setdefault(route, []).append(ms)
            hist = self.status.setdefault(route, {})
            hist[status] = hist.get(status, 0) + 1
            if status >= SERVER_ERROR or status == 0:
                self.samples.setdefault(
                    f"{route} {status}", body[:200].decode(errors="replace")
                )
            self.dead = self.dead + 1 if status == 0 else 0
            if self.dead >= DEAD_LIMIT:
                self.stopped.set()


def route_of(method: str, path: str) -> str:
    return f"{method} {UUID.sub('{id}', path.split('?', 1)[0])}"


def scoped(path: str, **params: str | None) -> str:
    query = urllib.parse.urlencode({k: v for k, v in params.items() if v})
    return f"{path}{'&' if '?' in path else '?'}{query}" if query else path


class Plan:
    def __init__(
        self, s: Session, project: str, target: str | None, scan: str | None
    ) -> None:
        self.project = project
        self.target = target
        self.scan = scan or self._newest_run(s)
        self.leads: dict[tuple[str, str | None], list[str]] = {}
        for scope in (self.scan, None):
            for dim in LEAD_DIMS:
                _, body, _ = s.send(
                    "POST",
                    scoped(f"/{dim}/search/leads", project_id=project, scan_id=scope),
                    {},
                )
                try:
                    leads = json.loads(body).get("leads", [])
                except (ValueError, AttributeError):
                    leads = []
                self.leads[(dim, scope)] = [x["query"] for x in leads][:COUNT_BATCH]

    def _newest_run(self, s: Session) -> str | None:
        if not self.target:
            return None
        path = scoped(
            "/scans",
            project_id=self.project,
            target_id=self.target,
            status="completed",
            sort_by="started",
            sort_dir="desc",
            size="1",
        )
        _, body, _ = s.send("GET", path)
        items = json.loads(body or b"{}").get("items") or []
        return items[0]["id"] if items else None

    def shell(self) -> list[Request]:
        p = self.project
        return [
            ("GET", "/auth/me", None),
            ("GET", "/projects", None),
            ("GET", "/instance-settings", None),
            ("GET", "/onboarding/status", None),
            ("GET", scoped("/whats-new/unseen", project_id=p, tz="UTC"), None),
            ("GET", scoped("/activity?page=1&size=30", project_id=p), None),
            ("GET", scoped("/notifications?page=1&size=50", project_id=p), None),
            ("GET", scoped("/notifications/stats", project_id=p), None),
            (
                "GET",
                scoped(
                    "/scans?status=pending&status=running&status=paused&sort_by=started"
                    "&sort_dir=desc&include_focused=true&size=50",
                    project_id=p,
                ),
                None,
            ),
            ("SSE", f"/events/stream?channels=broadcast,project:{p}", None),
        ]

    def dashboard(self) -> list[Request]:
        p = self.project
        return [
            *self.shell(),
            ("GET", scoped("/dashboard/overview?window=7d", project_id=p), None),
            ("GET", scoped("/dashboard/window?window=7d", project_id=p), None),
            ("GET", scoped("/dashboard/discovery", project_id=p), None),
            ("GET", "/dashboard/readiness", None),
            ("GET", scoped("/dashboard/activity?window=7d", project_id=p), None),
            ("GET", scoped("/schedules", project_id=p), None),
            ("GET", "/engines/catalog", None),
        ]

    def cells(self) -> list[Request]:
        p = self.project
        return [
            ("GET", scoped("/dashboard/surface-risk", project_id=p), None),
            ("GET", scoped("/dashboard/programs?window=7d", project_id=p), None),
            ("GET", scoped("/subdomains/facets", project_id=p), None),
            ("GET", scoped("/ips/facets", project_id=p), None),
            ("GET", scoped("/threat-intel/status", project_id=p), None),
            (
                "GET",
                scoped("/threat-intel/changes?days=7&limit=200", project_id=p),
                None,
            ),
            (
                "POST",
                scoped("/subdomains/search/counts", project_id=p),
                {
                    "filter": None,
                    "queries": [
                        "is:resolved",
                        "is:cdn",
                        "is:cloud",
                        "is:resolved and not is:cdn and not is:cloud",
                    ],
                },
            ),
            ("POST", scoped("/interest/project", project_id=p), {"limit": 6}),
            ("GET", scoped("/software/facets", project_id=p), None),
            ("GET", scoped("/software/coverage", project_id=p), None),
            ("GET", scoped("/subdomains/hygiene", project_id=p), None),
            ("GET", scoped("/ports/ai", project_id=p), None),
            ("GET", scoped("/domain-posture/project", project_id=p), None),
            ("GET", scoped("/subdomains/posture", project_id=p), None),
            ("GET", scoped("/subdomains/correlation-graph", project_id=p), None),
        ]

    def target_page(self) -> list[Request]:
        p, t, s = self.project, self.target, self.scan
        if not t:
            return []
        return [
            *self.shell(),
            ("GET", f"/targets/{t}", None),
            ("GET", f"/targets/{t}/detail", None),
            ("GET", scoped(f"/targets/{t}/summary", project_id=p), None),
            (
                "GET",
                scoped(
                    "/scans?sort_by=started&sort_dir=desc&include_focused=true&size=12",
                    project_id=p,
                    target_id=t,
                ),
                None,
            ),
            ("GET", scoped(f"/targets/{t}/programs", project_id=p), None),
            ("GET", f"/targets/{t}/seeds", None),
            ("GET", scoped("/notes?size=100", project_id=p, target_id=t), None),
            ("GET", "/engines/catalog", None),
            ("GET", scoped("/subdomains/hosting", scan_id=s, project_id=p), None),
            ("GET", scoped("/subdomains/facets", scan_id=s, project_id=p), None),
            ("GET", scoped("/subdomains/hygiene", scan_id=s, project_id=p), None),
            ("GET", scoped(f"/domain-posture/target/{t}", project_id=p), None),
            ("GET", scoped("/subdomains/posture", scan_id=s, project_id=p), None),
            ("GET", scoped("/subdomains/insights", scan_id=s, project_id=p), None),
            (
                "POST",
                scoped("/subdomains/search/counts", scan_id=s, project_id=p),
                {
                    "filter": None,
                    "queries": [
                        "not is:resolved and not is:web",
                        "is:resolved and not is:web",
                        "is:web and not is:vulnerable",
                        "is:web and is:vulnerable",
                    ],
                },
            ),
            ("POST", f"/interest/scan/{s}", {"limit": 6}),
            ("GET", scoped(f"/targets/{t}/estate", project_id=p, scan_id=s), None),
            ("GET", "/interest/catalog", None),
        ]

    def tabs(self, scope: str | None) -> list[Request]:
        p = self.project
        out: list[Request] = []
        for dim in (*LEAD_DIMS, "software", "secrets"):
            at = lambda path, d=dim: scoped(f"/{d}{path}", scan_id=scope, project_id=p)  # noqa: E731
            if dim == "endpoints":
                first: dict = {"page": 1, "size": 50}
            else:
                first = {"limit": 50, "offset": 0}
            search = "/search/issues" if dim == "vulnerabilities" else "/search"
            out.append(("POST", at(search), first))
            if dim in ("subdomains", "ports", "ips", "vulnerabilities", "software"):
                out.append(("GET", at("/facets"), None))
            if dim in LEAD_DIMS:
                out.append(("POST", at("/search/leads"), {}))
                out.append(("POST", at("/search/tabs"), {}))
                queries = self.leads.get((dim, scope)) or []
                if queries:
                    out.append(("POST", at("/search/counts"), {"queries": queries}))
        return out

    def scan_page(self) -> list[Request]:
        p, s = self.project, self.scan
        if not s:
            return []
        return [
            *self.shell(),
            ("GET", scoped(f"/scans/{s}", project_id=p), None),
            ("GET", scoped(f"/scans/{s}/activities", project_id=p), None),
            ("GET", scoped("/subdomains/insights", scan_id=s, project_id=p), None),
            ("GET", scoped("/vulnerabilities/overview", scan_id=s, project_id=p), None),
            ("GET", scoped("/endpoints/structure", scan_id=s, project_id=p), None),
            ("POST", f"/interest/scan/{s}", {"limit": 25, "offset": 0}),
            ("GET", scoped("/notes?size=100", project_id=p, scan_id=s), None),
            *self.tabs(s),
        ]

    def surface(self) -> list[Request]:
        return [*self.shell(), *self.tabs(None)]

    def typing(self) -> list[Request]:
        p = self.project
        out: list[Request] = []
        for dim in LEAD_DIMS:
            leads = self.leads.get((dim, self.scan)) or []
            fragment = random.choice(TYPED)  # noqa: S311
            queries = [fragment, *[f"{fragment} and {q}" for q in leads]][:COUNT_BATCH]
            path = scoped(f"/{dim}/search/counts", scan_id=self.scan, project_id=p)
            out.append(("POST", path, {"queries": queries}))
        return out

    def page(self, profile: str) -> list[Request]:
        if profile == "mixed":
            names = list(MIXED_WEIGHTS)
            weights = [MIXED_WEIGHTS[n] for n in names]
            profile = random.choices(names, weights=weights)[0]  # noqa: S311
        return {
            "dashboard": self.dashboard,
            "cells": self.cells,
            "target": self.target_page,
            "scan": self.scan_page,
            "surface": self.surface,
            "search-typing": self.typing,
        }[profile]()


def run_page(
    s: Session, requests: list[Request], stats: Stats, deadline: float
) -> None:
    for method, path, body in requests:
        if stats.stopped.is_set() or time.monotonic() > deadline:
            return
        if method == "SSE":
            status, ms = s.handshake(path)
            stats.add(SSE_ROUTE, status, ms)
            continue
        status, payload, ms = s.send(method, path, body)
        stats.add(route_of(method, path), status, ms, payload)


def client(
    sessions: list[Session],
    first: int,
    step: int,
    plan: Plan,
    profile: str,
    stats: Stats,
    deadline: float,
) -> int:
    pages = 0
    while time.monotonic() < deadline and not stats.stopped.is_set():
        session = sessions[(first + pages * step) % len(sessions)]
        run_page(session, plan.page(profile), stats, deadline)
        pages += 1
    return pages


def quantile(ms: list[float], q: float) -> float:
    return ms[min(len(ms) - 1, int(len(ms) * q))]


def summary(stats: Stats, wall: float) -> dict:
    routes = {}
    for route, ms in sorted(stats.ms.items()):
        ms.sort()
        hist = stats.status[route]
        routes[route] = {
            "calls": len(ms),
            "p50": round(statistics.median(ms)),
            "p95": round(quantile(ms, 0.95)),
            "p99": round(quantile(ms, 0.99)),
            "max": round(ms[-1]),
            "status": {str(k): v for k, v in sorted(hist.items())},
            "errors_5xx": sum(v for k, v in hist.items() if k >= SERVER_ERROR),
            "throttled": hist.get(THROTTLED, 0),
            "dropped": hist.get(0, 0),
        }
    calls = sum(r["calls"] for r in routes.values())
    return {
        "wall_seconds": round(wall, 1),
        "calls": calls,
        "rps": round(calls / wall, 1) if wall else 0,
        "stopped": stats.stopped.is_set(),
        "routes": routes,
        "samples": stats.samples,
    }


def print_summary(result: dict) -> None:
    print(
        f"{result['calls']} calls in {result['wall_seconds']} s, {result['rps']} per second"
        + (", stopped on dropped connections" if result["stopped"] else "")
    )
    head = f"{'route':58} {'calls':>6} {'p50':>7} {'p95':>7} {'p99':>7} {'max':>7} {'5xx':>4} {'429':>5} {'000':>4}"
    print(head)
    for route, r in result["routes"].items():
        print(
            f"{route[:58]:58} {r['calls']:6} {r['p50']:7} {r['p95']:7} {r['p99']:7} {r['max']:7}"
            f" {r['errors_5xx']:4} {r['throttled']:5} {r['dropped']:4}"
        )
    for key, sample in result["samples"].items():
        print(f"sample {key}: {sample[:200]!r}")


def accounts() -> list[tuple[str, str]]:
    path = os.environ.get("RENGINE_ACCOUNTS")
    if path:
        with Path(path).open(encoding="utf-8") as fh:
            pairs = [line.strip().split(":", 1) for line in fh if ":" in line]
        return [(u, p) for u, p in pairs]
    return [(os.environ["RENGINE_USER"], os.environ["RENGINE_PASSWORD"])]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project")
    parser.add_argument("--profile", choices=PROFILES, default="mixed")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--target-id")
    parser.add_argument("--scan-id")
    parser.add_argument(
        "--base", default=os.environ.get("RENGINE_URL", "http://127.0.0.1:8000")
    )
    parser.add_argument(
        "--warm", action="store_true", help="run each page once before timing"
    )
    parser.add_argument("--json", help="write the summary to this file")
    args = parser.parse_args()
    if not 1 <= args.concurrency <= MAX_CONCURRENCY:
        parser.error(f"--concurrency must be 1 to {MAX_CONCURRENCY}")

    sessions = [Session(args.base, u, p) for u, p in accounts()]
    plan = Plan(sessions[0], args.project, args.target_id, args.scan_id)
    print(f"profile {args.profile}, scan {plan.scan}, {len(sessions)} account(s)")
    if plan.scan is None and args.profile in {"target", "scan", "search-typing"}:
        message = "No completed run found for the target."
        raise SystemExit(message)
    if args.warm:
        names = list(MIXED_WEIGHTS) if args.profile == "mixed" else [args.profile]
        warm = Stats()
        for name in names:
            run_page(sessions[0], plan.page(name), warm, time.monotonic() + 600)
        print(f"warm pass: {sum(len(v) for v in warm.ms.values())} calls")

    stats = Stats()
    deadline = time.monotonic() + args.duration
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [
            pool.submit(
                client,
                sessions,
                i,
                args.concurrency,
                plan,
                args.profile,
                stats,
                deadline,
            )
            for i in range(args.concurrency)
        ]
        pages = sum(f.result() for f in futures)
    result = summary(stats, time.perf_counter() - t0)
    result.update(
        profile=args.profile,
        concurrency=args.concurrency,
        pages=pages,
        accounts=len(sessions),
    )
    print_summary(result)
    if args.json:
        with Path(args.json).open("w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=1)
    if result["stopped"]:
        sys.exit(2)


main()
