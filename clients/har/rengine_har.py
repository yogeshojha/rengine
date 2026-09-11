#!/usr/bin/env python3
"""Send a HAR file's traffic to reNgine's connector ingest endpoint.

Every proxy exports HAR — ZAP, mitmproxy, Burp, and every browser's developer tools —
so this is the path for any proxy without a native client.

    python3 rengine_har.py --endpoint https://rengine.example.com/api/v1/connectors/ingest \\
                           --token rngconn_... history.har

Nothing but the shape of each request is sent: the url, the method, the status, the
content type and the names of any body parameters. Headers, cookies and bodies stay on
your machine, exactly as the Burp client leaves them there.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

BATCH = 500
MAX_URL = 2000
MAX_PARAMS = 40
TIMEOUT = 30
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
# a header whose presence means the request carried a session
_AUTH_HEADERS = ("authorization", "cookie", "x-api-key", "x-auth-token")
_UNAUTHORIZED = 401


class TokenRefusedError(Exception):
    """The server rejected the token. Retrying just burns the rate limiter."""


def _text(value: Any, cap: int) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = "".join(c for c in value if c == "\t" or c >= " ").strip()
    return cleaned[:cap] or None


def _title(response: dict) -> str | None:
    content = response.get("content") or {}
    mime = (content.get("mimeType") or "").lower()
    if "html" not in mime:
        return None
    found = _TITLE.search(content.get("text") or "")
    return _text(found.group(1), 500) if found else None


def _authenticated(request: dict) -> bool:
    names = {
        (h.get("name") or "").lower()
        for h in (request.get("headers") or [])
        if isinstance(h, dict)
    }
    return any(name in names for name in _AUTH_HEADERS)


def _body_params(request: dict) -> list[str]:
    post = request.get("postData") or {}
    names = [
        _text(p.get("name"), 120)
        for p in (post.get("params") or [])
        if isinstance(p, dict)
    ]
    return list(dict.fromkeys(n for n in names if n))[:MAX_PARAMS]


def item(entry: dict) -> dict | None:
    """One HAR entry reduced to the shape reNgine stores. Headers never travel."""
    request = entry.get("request") or {}
    url = _text(request.get("url"), MAX_URL)
    if not url or not url.lower().startswith(("http://", "https://")):
        return None
    response = entry.get("response") or {}
    status = response.get("status")
    content = response.get("content") or {}
    size = content.get("size")
    if not isinstance(size, int) or size < 0:
        size = (
            response.get("bodySize")
            if isinstance(response.get("bodySize"), int)
            else None
        )
    return {
        "url": url,
        "method": (_text(request.get("method"), 16) or "GET").upper(),
        "status_code": status if isinstance(status, int) and status > 0 else None,
        "content_type": _text(content.get("mimeType"), 120),
        "content_length": size if isinstance(size, int) and size >= 0 else None,
        "title": _title(response),
        "authenticated": _authenticated(request),
        "source_tool": "proxy",
        "body_params": _body_params(request),
        "observed_at": _text(entry.get("startedDateTime"), 40),
    }


def read(path: Path) -> list[dict]:
    document = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    entries = ((document.get("log") or {}).get("entries")) or []
    if not isinstance(entries, list):
        return []
    return [row for row in (item(e) for e in entries if isinstance(e, dict)) if row]


def dedupe(items: list[dict]) -> list[dict]:
    """The server shapes and folds; this only keeps the wire small."""
    seen: set[tuple[str, str]] = set()
    kept = []
    for row in items:
        key = (row["method"], row["url"])
        if key in seen:
            continue
        seen.add(key)
        kept.append(row)
    return kept


def post(endpoint: str, token: str, batch: list[dict], client: str) -> dict:
    body = json.dumps({"client": client, "items": batch}).encode()
    request = urllib.request.Request(  # noqa: S310
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as e:
        detail = (e.read() or b"").decode("utf-8", errors="replace")[:300]
        if e.code == _UNAUTHORIZED:
            msg = "the token was refused; rotate it in reNgine rather than retrying"
            raise TokenRefusedError(msg) from e
        msg = f"ingest returned {e.code}: {detail}"
        raise SystemExit(msg) from e
    except urllib.error.URLError as e:
        msg = f"could not reach {endpoint}: {e.reason}"
        raise SystemExit(msg) from e


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("har", nargs="+", type=Path)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--client", default="har")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be sent and send nothing.",
    )
    args = parser.parse_args()

    items: list[dict] = []
    for path in args.har:
        if not path.is_file():
            print(f"skipping {path}: not a file", file=sys.stderr)
            continue
        try:
            items.extend(read(path))
        except (ValueError, OSError) as e:
            print(f"skipping {path}: {e}", file=sys.stderr)

    items = dedupe(items)
    if not items:
        print("nothing to send")
        return 0

    if args.dry_run:
        print(f"{len(items):,} requests would be sent to {args.endpoint}")
        for row in items[:10]:
            print(
                f"  {row['method']:6} {row['status_code'] or '---':>4} {row['url'][:90]}"
            )
        return 0

    totals = {"accepted": 0, "novel": 0, "dropped": 0, "queued": 0}
    try:
        for start in range(0, len(items), BATCH):
            result = post(
                args.endpoint, args.token, items[start : start + BATCH], args.client
            )
            for key in totals:
                totals[key] += int(result.get(key) or 0)
    except TokenRefusedError as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 1

    print(
        f"sent {len(items):,} requests: {totals['accepted']:,} accepted, "
        f"{totals['novel']:,} new shapes, {totals['dropped']:,} out of scope, "
        f"{totals['queued']:,} queued"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
