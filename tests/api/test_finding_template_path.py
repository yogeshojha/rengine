from __future__ import annotations

import uuid

import pytest

from shared.definitions.vulnerabilities import CUSTOM_ROOT, OFFICIAL_ROOT
from shared.models.vulnerability import VulnerabilityRead
from shared.utils.datetime import utc_now

pytestmark = pytest.mark.api


def _read(path: str | None) -> VulnerabilityRead:
    return VulnerabilityRead(
        id=uuid.uuid4(),
        scan_id=uuid.uuid4(),
        target_id=uuid.uuid4(),
        fingerprint="f",
        scanner="nuclei",
        template_id="t",
        template_name="T",
        template_path=path,
        severity="high",
        protocol="http",
        matched_at="https://example.com",
        discovered_at=utc_now(),
    )


@pytest.mark.parametrize(
    ("stored", "served"),
    [
        (
            f"{OFFICIAL_ROOT}/http/cves/2021/CVE-2021-1.yaml",
            "official/http/cves/2021/CVE-2021-1.yaml",
        ),
        (f"{CUSTOM_ROOT}/mine.yaml", "custom/mine.yaml"),
        ("official/http/a.yaml", "official/http/a.yaml"),
        (None, None),
    ],
)
def test_template_path_is_relative_to_the_library(stored, served):
    assert _read(stored).template_path == served


def test_serialised_row_names_no_worker_path():
    body = _read(f"{OFFICIAL_ROOT}/http/a.yaml").model_dump_json()
    assert "/app/" not in body
