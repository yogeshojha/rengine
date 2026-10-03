from types import SimpleNamespace

import pytest

from tools.katana.client import CHROME_BINARY, KatanaClient
from tools.runner.executor import tool_path

pytestmark = pytest.mark.pipeline


def _headless_args() -> list[str]:
    return KatanaClient._args(
        SimpleNamespace(
            depth=2,
            threads=10,
            timeout=10,
            crawl_scope="rdn",
            max_duration_minutes=0,
            rate_limit=None,
            include_js=False,
            form_extraction=False,
            ignore_query_params=False,
            exclude_extensions=[],
            headless=True,
            proxy_url=None,
            headers={},
        )
    )


def test_katana_launches_the_image_chromium_wrapper():
    args = _headless_args()
    assert "-headless" in args
    assert args[args.index("-system-chrome-path") + 1] == CHROME_BINARY
    assert CHROME_BINARY == "/usr/local/bin/chrome"


def test_katana_leaves_the_sandbox_to_the_wrapper():
    assert "-no-sandbox" not in _headless_args()


def test_tools_resolve_outside_root_home():
    assert tool_path().split(":")[0] == "/usr/local/bin"
