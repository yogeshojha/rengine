from __future__ import annotations

import pytest

from shared.services.vulnx import _row

pytestmark = pytest.mark.pipeline


def test_only_web_poc_urls_are_stored():
    row = _row(
        "CVE-2021-44228",
        {
            "pocs": [
                {"url": "https://github.com/a/poc", "source": "github"},
                {"url": "HTTP://example.com/poc"},
                {"url": "javascript:alert(1)"},
                {"url": "data:text/html,<script>"},
                {"url": "//evil.example/poc"},
                {"url": None},
            ]
        },
    )
    assert [p["url"] for p in row["pocs"]] == [
        "https://github.com/a/poc",
        "HTTP://example.com/poc",
    ]
