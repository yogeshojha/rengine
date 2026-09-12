"""The NVD corpus: every CVE and the version ranges it applies to, loaded from a keyless mirror."""

from __future__ import annotations

import csv
import json
import lzma
import shutil
import tempfile
import time
import urllib.request
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.definitions.vulnerabilities import Severity
from shared.logging import get_logger
from shared.utils.software import version_key, version_kind
from shared.utils.text import strip_control

logger = get_logger(__name__)

RELEASE = "https://github.com/fkie-cad/nvd-json-data-feeds/releases/latest/download"
FIRST_YEAR = 1999
DOWNLOAD_TIMEOUT = 60
FETCH_ATTEMPTS = 3
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_DESCRIPTION = 2000
RETRY_PAUSE = 2
USER_AGENT = "reNgine"

_CHUNK = 1 << 20
_ITEMS_KEY = '"cve_items"'
_METRIC_ORDER = (
    "cvssMetricV40",
    "cvssMetricV31",
    "cvssMetricV30",
    "cvssMetricV2",
)
_WILDCARDS = frozenset({"*", "-", ""})
_PARTS = frozenset({"a", "o"})
_MIN_CPE_FIELDS = 6
_REJECTED = "Rejected"

_SEVERITIES = {
    "CRITICAL": Severity.CRITICAL.value,
    "HIGH": Severity.HIGH.value,
    "MEDIUM": Severity.MEDIUM.value,
    "LOW": Severity.LOW.value,
    "NONE": Severity.INFO.value,
}


def _fetch(name: str, target: Path) -> int:
    """A stalled mirror connection is retried rather than waited out."""
    last: Exception | None = None
    for attempt in range(FETCH_ATTEMPTS):
        request = urllib.request.Request(  # noqa: S310
            f"{RELEASE}/{name}", headers={"User-Agent": USER_AGENT}
        )
        try:
            with (
                urllib.request.urlopen(  # noqa: S310
                    request, timeout=DOWNLOAD_TIMEOUT
                ) as response,
                target.open("wb") as handle,
            ):
                copied = 0
                while chunk := response.read(_CHUNK):
                    copied += len(chunk)
                    if copied > MAX_FILE_BYTES:
                        msg = f"{name} exceeded {MAX_FILE_BYTES} bytes"
                        raise ValueError(msg)
                    handle.write(chunk)
        except urllib.error.HTTPError:
            raise
        except (TimeoutError, OSError) as exc:
            last = exc
            logger.warning("nvd file retry", file=name, attempt=attempt + 1)
            time.sleep(RETRY_PAUSE)
            continue
        else:
            return copied
    raise last if last else RuntimeError(name)


def _iter_items(path: Path) -> Iterator[dict]:
    """Year files reach 250 MB decoded, so items are decoded one at a time."""
    decoder = json.JSONDecoder()
    with lzma.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        buf = ""
        while _ITEMS_KEY not in buf:
            chunk = handle.read(_CHUNK)
            if not chunk:
                return
            buf += chunk
        buf = buf[buf.index(_ITEMS_KEY) + len(_ITEMS_KEY) :]
        while "[" not in buf:
            chunk = handle.read(_CHUNK)
            if not chunk:
                return
            buf += chunk
        buf = buf[buf.index("[") + 1 :]
        while True:
            buf = buf.lstrip(" \t\r\n,")
            if buf.startswith("]"):
                return
            try:
                item, end = decoder.raw_decode(buf)
            except ValueError:
                chunk = handle.read(_CHUNK)
                if not chunk:
                    return
                buf += chunk
                continue
            buf = buf[end:]
            yield item


def _as_datetime(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.isoformat()


def _score(item: dict) -> tuple[float | None, str | None, str | None]:
    metrics = item.get("metrics") or {}
    for key in _METRIC_ORDER:
        entries = metrics.get(key) or []
        if not entries:
            continue
        data = entries[0].get("cvssData") or {}
        severity = data.get("baseSeverity") or entries[0].get("baseSeverity")
        return (
            data.get("baseScore"),
            _SEVERITIES.get(str(severity).upper()),
            str(data.get("vectorString") or "")[:200] or None,
        )
    return None, None, None


def _description(item: dict) -> str | None:
    for entry in item.get("descriptions") or []:
        if entry.get("lang") == "en":
            return strip_control(entry.get("value") or "")[:MAX_DESCRIPTION] or None
    return None


def _nodes(node: dict, out: list[dict]) -> None:
    out.extend(node.get("cpeMatch") or [])
    for child in node.get("nodes") or []:
        _nodes(child, out)


def _bounds(
    match: dict,
) -> tuple[str, str | None, str | None, bool, str | None, bool] | None:
    """A criteria with no version statement matches every release, so it is not a match."""
    parts = match["criteria"].split(":")
    if len(parts) < _MIN_CPE_FIELDS or parts[2] not in _PARTS:
        return None
    exact = parts[5]
    start_raw = match.get("versionStartIncluding") or match.get("versionStartExcluding")
    end_raw = match.get("versionEndIncluding") or match.get("versionEndExcluding")
    values = [v for v in (start_raw, end_raw) if v] or (
        [] if exact in _WILDCARDS else [exact]
    )
    keys = [version_key(v) for v in values]
    kinds = {version_kind(k) for k in keys if k}
    if not keys or not all(keys) or len(kinds) != 1:
        return None
    kind = kinds.pop()
    exact_key = None if exact in _WILDCARDS else version_key(exact)
    if kind is None or (exact_key is not None and version_kind(exact_key) != kind):
        return None
    return (
        kind,
        version_key(start_raw) if start_raw else None,
        exact_key,
        bool(match.get("versionStartIncluding")),
        version_key(end_raw) if end_raw else None,
        bool(match.get("versionEndIncluding")),
    )


def _match_rows(item: dict) -> Iterator[tuple[Any, ...]]:
    cve = item["id"]
    for config in item.get("configurations") or []:
        conditional = config.get("operator") == "AND"
        matches: list[dict] = []
        for node in config.get("nodes") or []:
            _nodes(node, matches)
        for match in matches:
            if not match.get("vulnerable"):
                continue
            bounds = _bounds(match)
            if bounds is None:
                continue
            kind, start_key, exact_key, start_incl, end_key, end_incl = bounds
            parts = match["criteria"].split(":")
            yield (
                cve,
                strip_control(parts[3])[:200],
                strip_control(parts[4])[:200],
                kind,
                exact_key,
                start_key,
                start_incl,
                end_key,
                end_incl,
                conditional,
            )


def _copy(session: Session, table: str, columns: str, path: Path) -> None:
    raw = session.connection().connection
    cursor = raw.cursor()
    with path.open("r", encoding="utf-8") as handle:
        cursor.copy_expert(
            f"COPY {table} ({columns}) FROM STDIN WITH (FORMAT csv)", handle
        )


def load(
    session: Session, current_version: str | None = None
) -> tuple[int, str | None, int]:
    """Rebuild the corpus from the published year files."""
    stamp = _release_stamp()
    if stamp and stamp == current_version and corpus_ready(session):
        held = int(
            session.execute(text("SELECT count(*) FROM nvd_cpe_matches")).scalar() or 0
        )
        logger.info("nvd corpus unchanged", stamp=stamp, matches=held)
        return held, stamp, 0
    workdir = Path(tempfile.mkdtemp(prefix="nvd_corpus_"))
    downloaded = 0
    cve_count = 0
    match_count = 0
    last_year = datetime.now(UTC).year
    try:
        cve_path = workdir / "cves.csv"
        match_path = workdir / "matches.csv"
        seen: set[str] = set()
        with (
            cve_path.open("w", encoding="utf-8", newline="") as cve_file,
            match_path.open("w", encoding="utf-8", newline="") as match_file,
        ):
            cves = csv.writer(cve_file)
            matches = csv.writer(match_file)
            for year in range(FIRST_YEAR, last_year + 1):
                name = f"CVE-{year}.json.xz"
                target = workdir / name
                try:
                    downloaded += _fetch(name, target)
                except Exception:
                    logger.warning("nvd year feed unavailable", year=year)
                    continue
                for item in _iter_items(target):
                    if item.get("vulnStatus") == _REJECTED:
                        continue
                    cve = item.get("id")
                    if not cve or cve in seen:
                        continue
                    seen.add(cve)
                    score, severity, vector = _score(item)
                    cves.writerow(
                        [
                            cve[:30],
                            severity or "",
                            "" if score is None else score,
                            vector or "",
                            _description(item) or "",
                            _as_datetime(item.get("published")) or "",
                            _as_datetime(item.get("lastModified")) or "",
                        ]
                    )
                    cve_count += 1
                    for row in _match_rows(item):
                        matches.writerow(
                            ["" if value is None else value for value in row]
                        )
                        match_count += 1
                target.unlink(missing_ok=True)
                logger.info(
                    "nvd year loaded", year=year, cves=cve_count, matches=match_count
                )

        session.execute(text("TRUNCATE TABLE nvd_cpe_matches"))
        session.execute(text("TRUNCATE TABLE nvd_cves"))
        _copy(
            session,
            "nvd_cves",
            "cve, severity, cvss_score, cvss_vector, description, published_at, last_modified_at",
            cve_path,
        )
        _copy(
            session,
            "nvd_cpe_matches",
            "cve, vendor, product, version_kind, exact_key, start_key, "
            "start_incl, end_key, end_incl, conditional",
            match_path,
        )
        logger.info("nvd corpus loaded", cves=cve_count, matches=match_count)
        return match_count, stamp, downloaded
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _release_stamp() -> str | None:
    """The mirror publishes the release date beside the files."""
    try:
        request = urllib.request.Request(  # noqa: S310
            f"{RELEASE}/CVE-modified.meta", headers={"User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:  # noqa: S310
            for line in response.read(4096).decode("utf-8", "replace").splitlines():
                if line.startswith("lastModifiedDate:"):
                    return line.split(":", 1)[1].strip()[:100]
    except Exception:
        logger.debug("nvd release stamp unavailable", exc_info=True)
    return None


def corpus_ready(session: Session) -> bool:
    return bool(session.execute(text("SELECT 1 FROM nvd_cpe_matches LIMIT 1")).scalar())
