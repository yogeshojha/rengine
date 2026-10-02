"""Vendored and uploaded typefaces."""

from __future__ import annotations

import base64
import re
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select

from shared.definitions.report_fonts import FONT_ROLES, FONT_ROOT, FontOrigin, FontRole
from shared.definitions.reports import FONT_FAMILIES
from shared.models.report import FontFace, ReportFont, ReportFontRead

ASSETS = Path(__file__).resolve().parent / "assets"
VENDORED_CSS = ASSETS / "fonts.css"
CUSTOM_ROOT = Path(FONT_ROOT)


def _face_path(slug: str, filename: str) -> Path | None:
    directory = (CUSTOM_ROOT / slug).resolve()
    candidate = (directory / filename).resolve()
    if not directory.is_relative_to(CUSTOM_ROOT.resolve()):
        return None
    if not candidate.is_relative_to(directory) or not candidate.is_file():
        return None
    return candidate


_VENDORED_FACE_RE = re.compile(
    r"font-family:'([^']+)';font-style:(\w+);font-weight:(\d+);.*?url\('fonts/([^']+)'\)"
)


def _vendored_faces() -> dict[str, list[FontFace]]:
    faces: dict[str, list[FontFace]] = {}
    if not VENDORED_CSS.is_file():
        return faces
    for found in _VENDORED_FACE_RE.finditer(VENDORED_CSS.read_text(encoding="utf-8")):
        family, style, weight, filename = found.groups()
        path = ASSETS / "fonts" / filename
        faces.setdefault(family, []).append(
            FontFace(
                weight=int(weight),
                italic=style == "italic",
                filename=filename,
                bytes=path.stat().st_size if path.is_file() else 0,
            )
        )
    return faces


@lru_cache(maxsize=1)
def vendored() -> list[ReportFontRead]:
    faces = _vendored_faces()
    return [
        ReportFontRead(
            slug=spec.key,
            name=spec.label,
            role=spec.role,
            origin=FontOrigin.BUILTIN.value,
            note=spec.note,
            faces=faces.get(spec.label, []),
            weights=sorted({f.weight for f in faces.get(spec.label, [])}),
            bytes=sum(f.bytes for f in faces.get(spec.label, [])),
        )
        for spec in FONT_FAMILIES
    ]


def font_read(row: ReportFont) -> ReportFontRead:
    faces = [FontFace.model_validate(f) for f in (row.faces or [])]
    return ReportFontRead(
        id=row.id,
        slug=row.slug,
        name=row.name,
        role=row.role if row.role in FONT_ROLES else FontRole.SANS.value,
        origin=row.origin,
        note=row.note,
        faces=faces,
        weights=sorted({f.weight for f in faces}),
        bytes=row.bytes,
        created_at=row.created_at,
    )


def custom(session) -> list[ReportFontRead]:
    rows = session.execute(select(ReportFont).order_by(ReportFont.name)).scalars().all()
    return [font_read(row) for row in rows]


def families(session) -> list[ReportFontRead]:
    return [*vendored(), *custom(session)]


def _face_css(
    name: str, weight: int, style: str, src: str, fmt: str, span: str = ""
) -> str:
    return (
        f"@font-face{{font-family:'{name}';font-style:{style};font-weight:{weight};"
        f"font-display:swap;src:url('{src}') format('{fmt}'){span}}}"
    )


_FAMILY_RE = re.compile(r"font-family:'([^']+)'")


def vendored_css(*, embed: bool, only: frozenset[str] | None = None) -> str:
    if not VENDORED_CSS.is_file():
        return ""
    wanted = None
    if only is not None:
        by_key = {f.key: f.label for f in FONT_FAMILIES}
        wanted = {by_key[k] for k in only if k in by_key}

    def replace(match: re.Match) -> str:
        path = ASSETS / "fonts" / match.group(1)
        if not path.is_file():
            return match.group(0)
        if not embed:
            return f"url('{path.as_uri()}')"
        payload = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"url('data:font/woff2;base64,{payload}')"

    blocks = []
    for line in VENDORED_CSS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if wanted is not None:
            found = _FAMILY_RE.search(line)
            if found and found.group(1) not in wanted:
                continue
        blocks.append(re.sub(r"url\('fonts/([^']+)'\)", replace, line))
    return "\n".join(blocks)


def custom_css(session, *, embed: bool, only: frozenset[str] | None = None) -> str:
    rules: list[str] = []
    for family in custom(session):
        if only is not None and family.slug not in only:
            continue
        for face in family.faces:
            path = _face_path(family.slug, face.filename)
            if path is None:
                continue
            style = "italic" if face.italic else "normal"
            if embed:
                payload = base64.b64encode(path.read_bytes()).decode("ascii")
                src = f"data:font/{face.format};base64,{payload}"
            else:
                src = path.as_uri()
            rules.append(_face_css(family.name, face.weight, style, src, face.format))
    return "\n".join(rules)


def font_faces(
    session=None, *, embed: bool = False, only: frozenset[str] | None = None
) -> str:
    css = vendored_css(embed=embed, only=only)
    if session is not None:
        extra = custom_css(session, embed=embed, only=only)
        if extra:
            css = f"{css}\n{extra}"
    return css
