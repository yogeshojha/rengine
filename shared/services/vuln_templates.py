"""The vulnerability check library: index the project templates, accept uploads, resolve a plan."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import urllib.request
import zipfile
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import and_, cast, delete, false, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import array as pg_array
from sqlalchemy.orm import Session

from shared.definitions.vulnerabilities import (
    CUSTOM_ROOT,
    FORBIDDEN_TEMPLATE_KEYS,
    MAX_TEMPLATE_BYTES,
    OFFICIAL_ROOT,
    TEMPLATE_SET_BY_KEY,
    TEMPLATE_SETS,
    Protocol,
    Severity,
    TemplateOrigin,
    coerce_severity,
    is_kev,
)
from shared.logging import get_logger
from shared.models.vuln_template import TemplateSelection, VulnTemplate
from shared.utils.datetime import utc_now
from shared.utils.text import strip_control

logger = get_logger(__name__)

ARCHIVE_URL = (
    "https://codeload.github.com/projectdiscovery/nuclei-templates/zip/refs/heads/main"
)
DOWNLOAD_TIMEOUT = 300
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_EXTRACTED_BYTES = 1024 * 1024 * 1024

_PROTOCOL_KEYS: tuple[tuple[str, str], ...] = (
    ("http", Protocol.HTTP.value),
    ("requests", Protocol.HTTP.value),
    ("network", Protocol.NETWORK.value),
    ("tcp", Protocol.NETWORK.value),
    ("dns", Protocol.DNS.value),
    ("ssl", Protocol.SSL.value),
    ("file", Protocol.FILE.value),
    ("headless", Protocol.HEADLESS.value),
    ("javascript", Protocol.JAVASCRIPT.value),
    ("websocket", Protocol.WEBSOCKET.value),
    ("whois", Protocol.WHOIS.value),
)

# directories in the upstream archive that hold no runnable check
_SKIP_DIRS = frozenset({".github", ".git", "helpers", "profiles", "workflows"})
_clean = strip_control


class TemplateError(ValueError):
    """An uploaded document is not a usable check."""


@dataclass
class ParsedTemplate:
    template_id: str
    name: str
    severity: str
    protocol: str
    description: str | None = None
    remediation: str | None = None
    tags: list[str] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    cve_ids: list[str] = field(default_factory=list)
    cwe_ids: list[str] = field(default_factory=list)
    cvss_score: float | None = None
    requests: int = 0


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [_clean(p).strip() for p in value.replace("\n", ",").split(",")]
        return [p for p in parts if p]
    if isinstance(value, (list, tuple, set)):
        out: list[str] = []
        for item in value:
            out.extend(_as_list(item))
        return out
    return [_clean(str(value))]


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = _clean(str(value)).strip()
    return text or None


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _protocol_of(document: dict) -> str:
    for key, protocol in _PROTOCOL_KEYS:
        if key in document:
            return protocol
    return Protocol.OTHER.value


def _request_count(document: dict, info: dict) -> int:
    stated = (info.get("metadata") or {}).get("max-request")
    counted = _as_float(stated)
    if counted:
        return int(counted)
    for key, _protocol in _PROTOCOL_KEYS:
        block = document.get(key)
        if isinstance(block, list):
            return len(block)
    return 1


def parse_template(raw: str) -> ParsedTemplate:
    """Read one nuclei document into the library's row shape, or say why it cannot be used."""
    if len(raw.encode("utf-8", "ignore")) > MAX_TEMPLATE_BYTES:
        msg = "Document is larger than the template size limit."
        raise TemplateError(msg)
    try:
        document = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        msg = f"Not valid YAML: {str(exc).splitlines()[0][:160]}"
        raise TemplateError(msg) from exc
    if not isinstance(document, dict):
        msg = "A template must be a YAML mapping."
        raise TemplateError(msg)

    forbidden = FORBIDDEN_TEMPLATE_KEYS & set(document)
    if forbidden:
        names = ", ".join(sorted(forbidden))
        msg = f"Uses the {names} protocol, which executes commands on the scanner. Not accepted."
        raise TemplateError(msg)

    template_id = _as_text(document.get("id"))
    if not template_id:
        msg = "Missing the top-level id field."
        raise TemplateError(msg)

    info = document.get("info")
    if not isinstance(info, dict):
        msg = "Missing the info block."
        raise TemplateError(msg)
    name = _as_text(info.get("name"))
    if not name:
        msg = "Missing info.name."
        raise TemplateError(msg)

    protocol = _protocol_of(document)
    if protocol == Protocol.OTHER.value and "workflows" not in document:
        msg = "Declares no protocol block, so it would never run."
        raise TemplateError(msg)

    classification = info.get("classification")
    classification = classification if isinstance(classification, dict) else {}
    return ParsedTemplate(
        template_id=template_id[:200],
        name=name[:500],
        severity=coerce_severity(_as_text(info.get("severity"))),
        protocol=protocol,
        description=_as_text(info.get("description")),
        remediation=_as_text(info.get("remediation")),
        tags=_as_list(info.get("tags"))[:60],
        authors=_as_list(info.get("author"))[:20],
        references=_as_list(info.get("reference"))[:40],
        cve_ids=[c.upper() for c in _as_list(classification.get("cve-id"))][:20],
        cwe_ids=[c.upper() for c in _as_list(classification.get("cwe-id"))][:20],
        cvss_score=_as_float(classification.get("cvss-score")),
        requests=_request_count(document, info),
    )


def sets_for(tags: Iterable[str], path: str) -> list[str]:
    """The curated sets a check belongs to. A check may belong to several, or to none."""
    lowered = {t.lower() for t in tags or ()}
    normalized = path.replace("\\", "/").lstrip("/")
    keys = []
    for spec in TEMPLATE_SETS:
        by_tag = bool(lowered & set(spec.tags))
        by_dir = any(normalized.startswith(d) for d in spec.dirs)
        if by_tag or by_dir:
            keys.append(spec.key)
    return keys


def _row(
    parsed: ParsedTemplate,
    *,
    origin: str,
    path: str,
    raw: str | None,
    uploaded_by=None,
) -> dict:
    now = utc_now()
    return {
        "origin": origin,
        "template_id": parsed.template_id,
        "path": path[:500],
        "name": parsed.name,
        "severity": parsed.severity,
        "protocol": parsed.protocol,
        "directory": str(Path(path).parent).replace("\\", "/")[:200],
        "description": parsed.description,
        "remediation": parsed.remediation,
        "tags": parsed.tags,
        "authors": parsed.authors,
        "references": parsed.references,
        "cve_ids": parsed.cve_ids,
        "cwe_ids": parsed.cwe_ids,
        "cvss_score": parsed.cvss_score,
        "requests": parsed.requests,
        "digest": hashlib.sha256((raw or path).encode("utf-8", "ignore")).hexdigest(),
        "raw": raw,
        "enabled": True,
        "uploaded_by": uploaded_by,
        "created_at": now,
        "updated_at": now,
    }


def official_root() -> Path:
    return Path(OFFICIAL_ROOT)


def custom_root() -> Path:
    return Path(CUSTOM_ROOT)


def library_ready(session: Session) -> bool:
    return bool(
        session.scalar(
            select(func.count())
            .select_from(VulnTemplate)
            .where(VulnTemplate.origin == TemplateOrigin.OFFICIAL.value)
            .limit(1)
        )
    )


@contextmanager
def _downloaded_archive() -> Iterator[Path]:
    workdir = Path(tempfile.mkdtemp(prefix="vuln_templates_"))
    archive = workdir / "templates.zip"
    try:
        request = urllib.request.Request(  # noqa: S310
            ARCHIVE_URL, headers={"User-Agent": "reNgine"}
        )
        with (
            urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response,  # noqa: S310
            archive.open("wb") as handle,
        ):
            copied = 0
            while chunk := response.read(1 << 20):
                copied += len(chunk)
                if copied > MAX_ARCHIVE_BYTES:
                    msg = "Template archive exceeded the download limit."
                    raise ValueError(msg)
                handle.write(chunk)
        yield archive
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _extract(archive: Path, destination: Path) -> int:
    staging = destination.parent / f"{destination.name}.incoming"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)
    written = 0
    total = 0
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            if entry.is_dir() or not entry.filename.lower().endswith((".yaml", ".yml")):
                continue
            parts = Path(entry.filename).parts[1:]
            if not parts or any(
                p in _SKIP_DIRS or p.startswith(".") for p in parts[:-1]
            ):
                continue
            total += entry.file_size
            if total > MAX_EXTRACTED_BYTES:
                msg = "Template archive expanded beyond the size limit."
                raise ValueError(msg)
            target = staging.joinpath(*parts).resolve()
            if not str(target).startswith(str(staging.resolve())):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(entry) as source, target.open("wb") as handle:
                shutil.copyfileobj(source, handle)
            written += 1
    if not written:
        msg = "Template archive held no checks."
        raise ValueError(msg)
    previous = destination.parent / f"{destination.name}.previous"
    shutil.rmtree(previous, ignore_errors=True)
    if destination.exists():
        destination.rename(previous)
    staging.rename(destination)
    shutil.rmtree(previous, ignore_errors=True)
    return written


def index_directory(session: Session, root: Path, origin: str) -> int:
    """Replace every row of this origin with what the directory holds now."""
    rows: list[dict] = []
    for path in sorted(root.rglob("*.y*ml")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if any(
            part in _SKIP_DIRS or part.startswith(".")
            for part in Path(relative).parts[:-1]
        ):
            continue
        try:
            parsed = parse_template(path.read_text(encoding="utf-8", errors="replace"))
        except (TemplateError, OSError) as exc:
            logger.debug("skipping template", path=relative, reason=str(exc)[:120])
            continue
        rows.append(_row(parsed, origin=origin, path=relative, raw=None))

    session.execute(delete(VulnTemplate).where(VulnTemplate.origin == origin))
    for start in range(0, len(rows), 1000):
        session.execute(VulnTemplate.__table__.insert(), rows[start : start + 1000])
    session.commit()
    return len(rows)


def sync_official(session: Session) -> int:
    """Refresh the project template set. A failed download leaves the last good copy in place."""
    root = official_root()
    root.parent.mkdir(parents=True, exist_ok=True)
    with _downloaded_archive() as archive:
        extracted = _extract(archive, root)
    logger.info("nuclei templates extracted", count=extracted, path=str(root))
    return index_directory(session, root, TemplateOrigin.OFFICIAL.value)


def store_custom(raw: str, filename: str) -> tuple[ParsedTemplate, str]:
    """Validate an uploaded document and write it under the custom root."""
    parsed = parse_template(raw)
    stem = Path(filename).stem or parsed.template_id
    safe = "".join(c for c in stem if c.isalnum() or c in "-_.")[:80] or "template"
    relative = f"{safe}-{parsed.template_id.lower()[:60]}.yaml".replace("--", "-")
    root = custom_root()
    root.mkdir(parents=True, exist_ok=True)
    (root / relative).write_text(raw, encoding="utf-8")
    return parsed, relative


def custom_row(parsed: ParsedTemplate, relative: str, raw: str, uploaded_by) -> dict:
    return _row(
        parsed,
        origin=TemplateOrigin.CUSTOM.value,
        path=relative,
        raw=raw,
        uploaded_by=uploaded_by,
    )


def _tags_overlap(values: Iterable[str]):
    wanted = sorted({v.strip().lower() for v in values if v and v.strip()})
    if not wanted:
        return None
    return func.jsonb_exists_any(cast(VulnTemplate.tags, JSONB), pg_array(wanted))


def _set_predicate(keys: Iterable[str]):
    branches = []
    tags: list[str] = []
    for key in keys:
        spec = TEMPLATE_SET_BY_KEY.get(key)
        if spec is None:
            continue
        tags.extend(spec.tags)
        branches.extend(
            VulnTemplate.path.like(f"{directory}/%") for directory in spec.dirs
        )
    overlap = _tags_overlap(tags)
    if overlap is not None:
        branches.append(overlap)
    return or_(*branches) if branches else None


def selection_predicate(selection: TemplateSelection, *, official_only: bool = True):
    """The library rows a plan selects, as one predicate over VulnTemplate."""
    clauses = [VulnTemplate.enabled.is_(True)]
    if official_only:
        clauses.append(VulnTemplate.origin == TemplateOrigin.OFFICIAL.value)
    # an empty axis means the user cleared it, which selects nothing — never everything
    clauses.append(VulnTemplate.severity.in_(list(selection.severities)))
    chosen = _set_predicate(selection.template_sets)
    extra = _tags_overlap(selection.include_tags)
    reach = [c for c in (chosen, extra) if c is not None]
    if reach:
        clauses.append(or_(*reach))
    else:
        clauses.append(false())
    excluded = _tags_overlap(selection.exclude_tags)
    if excluded is not None:
        clauses.append(~excluded)
    if selection.exclude_templates:
        clauses.append(
            VulnTemplate.template_id.notin_(list(selection.exclude_templates))
        )
    if not selection.headless:
        clauses.append(VulnTemplate.protocol != Protocol.HEADLESS.value)
    # file checks read the scanner's own disk, so they never apply to a remote target
    clauses.append(VulnTemplate.protocol != Protocol.FILE.value)
    return and_(*clauses)


def selected_templates(
    session: Session, selection: TemplateSelection
) -> list[VulnTemplate]:
    rows = list(
        session.execute(
            select(VulnTemplate).where(selection_predicate(selection))
        ).scalars()
    )
    if selection.custom_templates:
        rows.extend(
            session.execute(
                select(VulnTemplate).where(
                    VulnTemplate.id.in_(list(selection.custom_templates)),
                    VulnTemplate.enabled.is_(True),
                )
            )
            .scalars()
            .all()
        )
    return rows


def severity_of(rows: Iterable[VulnTemplate]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.severity] = counts.get(row.severity, 0) + 1
    return counts


def kev_rows(rows: Iterable[VulnTemplate]) -> int:
    return sum(1 for row in rows if is_kev(row.tags))


__all__ = [
    "ParsedTemplate",
    "Severity",
    "TemplateError",
    "custom_root",
    "custom_row",
    "index_directory",
    "kev_rows",
    "library_ready",
    "official_root",
    "parse_template",
    "selected_templates",
    "selection_predicate",
    "sets_for",
    "severity_of",
    "store_custom",
    "sync_official",
]
