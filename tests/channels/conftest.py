from __future__ import annotations

from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if item.path.resolve().is_relative_to(_HERE):
            item.add_marker(pytest.mark.channels)
