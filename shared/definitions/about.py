"""Where the project publishes its releases, documentation and issues."""

from __future__ import annotations

import re

REPOSITORY_URL = "https://github.com/yogeshojha/rengine"
DOCUMENTATION_URL = "https://rengine.wiki"
ISSUE_URL = f"{REPOSITORY_URL}/issues/new?template=bug_report.yaml"

_RELEASE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?$")


def release_url(version: str) -> str | None:
    """The GitHub release of a tagged version, None for any other build."""
    return (
        f"{REPOSITORY_URL}/releases/tag/v{version}" if _RELEASE.match(version) else None
    )
