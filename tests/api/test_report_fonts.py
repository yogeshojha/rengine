from __future__ import annotations

import re

import pytest

from reports.fonts import ASSETS, VENDORED_CSS
from shared.definitions.reports import FONT_FAMILIES

CSS = VENDORED_CSS.read_text(encoding="utf-8")


@pytest.mark.parametrize("spec", FONT_FAMILIES, ids=lambda s: s.key)
def test_every_family_has_vendored_faces(spec):
    assert f"font-family:'{spec.label}'" in CSS


@pytest.mark.parametrize("filename", re.findall(r"url\('fonts/([^']+)'\)", CSS))
def test_every_face_file_exists(filename):
    assert (ASSETS / "fonts" / filename).is_file()
