from __future__ import annotations

import pytest

from shared.definitions.exports import (
    BUNDLE,
    EXPORT_FORMATS,
    EXPORT_STATUS_LABELS,
    FORMAT_LABELS,
    LIVE_STATUSES,
    ExportFormat,
    ExportStatus,
)
from tests.grammar.ts_mirror import Mirror

pytestmark = pytest.mark.grammar


@pytest.fixture(scope="module")
def mirror() -> Mirror:
    return Mirror("exports.ts")


def test_the_frontend_mirror_carries_every_format(mirror: Mirror):
    assert mirror.values("ExportFormat") == {f.value for f in ExportFormat}
    assert set(mirror.const("EXPORT_FORMATS")) == set(EXPORT_FORMATS)
    assert mirror.labels("FORMAT_LABELS") == FORMAT_LABELS
    assert mirror.const("BUNDLE") == BUNDLE


def test_the_frontend_mirror_carries_every_status(mirror: Mirror):
    assert mirror.values("ExportStatus") == {s.value for s in ExportStatus}
    assert mirror.labels("EXPORT_STATUS_LABELS") == EXPORT_STATUS_LABELS
    assert set(mirror.labels("EXPORT_STATUS_TONE")) == {s.value for s in ExportStatus}
    assert tuple(mirror.const("LIVE")) == LIVE_STATUSES
