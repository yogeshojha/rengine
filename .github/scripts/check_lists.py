"""Fail when a hand-kept copy of the Python package list drifts from the Makefile.

The Makefile's PACKAGES is the one list of Python packages. Tools that cannot
read it keep their own copy: the pre-commit hook pattern, the compose mounts,
the Dockerfile COPY lines and the api's reload directories. This script reads
each copy and reports every place that disagrees.

Usage (from the Makefile): check_lists.py --ruff <version> <package>...
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# top-level directories that hold Python but are deliberately not linted
NOT_LINTED = {
    "alembic": "migrations are hand-written and applied as they stand",
    "scripts": "maintenance CLIs outside every image",
}
# ignored when looking for Python directories
SKIPPED = {".git", ".venv", "node_modules", "frontend", "clients", "research"}
# packages the images run but that are not reloadable code
NOT_CODE = {"tests"}

COPY_LINE = re.compile(r"^COPY (?P<src>[\w./-]+) /app/(?P<dst>[\w.-]+)$", re.MULTILINE)
MOUNT_LINE = re.compile(r"^\s*- \./(?P<src>[\w./-]+):/app/(?P<dst>[\w.-]+)(?::ro)?$")


def _top(path: str) -> str:
    return path.split("/", 1)[0]


def compose_anchor(text: str, anchor: str) -> list[str]:
    """Return the list items under the ``&anchor`` sequence, up to the blank line."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.endswith(f"&{anchor}"))
    items = []
    for line in lines[start + 1 :]:
        if not line.strip():
            break
        items.append(line)
    return items


def code_dirs(pairs: list[tuple[str, str]], packages: set[str]) -> set[str]:
    """The /app directories filled from a Python package, tests aside."""
    return {
        dst
        for src, dst in pairs
        if _top(src) in packages and _top(src) not in NOT_CODE and (ROOT / src).is_dir()
    }


def mount_pairs(lines: list[str]) -> list[tuple[str, str]]:
    return [(m["src"], m["dst"]) for line in lines if (m := MOUNT_LINE.match(line))]


def copy_pairs(dockerfile: Path) -> list[tuple[str, str]]:
    text = dockerfile.read_text()
    return [(m["src"], m["dst"]) for m in COPY_LINE.finditer(text)]


def python_dirs() -> set[str]:
    return {
        child.name
        for child in ROOT.iterdir()
        if child.is_dir()
        and child.name not in SKIPPED
        and not child.name.startswith(".")
        and next(child.rglob("*.py"), None) is not None
    }


def compare(problems: list[str], label: str, found: set[str], expected: set[str]):
    if found != expected:
        missing = ", ".join(sorted(expected - found)) or "-"
        extra = ", ".join(sorted(found - expected)) or "-"
        problems.append(f"{label}: missing {missing}; not expected {extra}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ruff", required=True)
    parser.add_argument("packages", nargs="+")
    args = parser.parse_args()
    packages = set(args.packages)
    problems: list[str] = []

    unlinted = python_dirs() - packages - NOT_LINTED.keys()
    if unlinted:
        problems.append(
            "Makefile PACKAGES: Python directories that nothing lints: "
            + ", ".join(sorted(unlinted))
        )

    precommit = (ROOT / ".pre-commit-config.yaml").read_text()
    pattern = re.search(r"&packages \^\((?P<names>[\w|]+)\)/", precommit)
    compare(
        problems,
        ".pre-commit-config.yaml &packages",
        set(pattern["names"].split("|")) if pattern else set(),
        packages,
    )
    rev = re.search(r"astral-sh/ruff-pre-commit\n\s+rev: v(?P<rev>\S+)", precommit)
    if not rev or rev["rev"] != args.ruff:
        problems.append(
            f".pre-commit-config.yaml ruff rev: expected v{args.ruff} "
            "(pyproject.toml pins it)"
        )

    compose = (ROOT / "docker-compose.yml").read_text()
    api_mounted = code_dirs(
        mount_pairs(compose_anchor(compose, "api-volumes")), packages
    )
    worker_mounted = code_dirs(
        mount_pairs(compose_anchor(compose, "worker-volumes")), packages
    )
    api_copied = code_dirs(copy_pairs(ROOT / "api" / "Dockerfile"), packages)
    worker_copied = code_dirs(copy_pairs(ROOT / "worker" / "Dockerfile"), packages)
    compare(problems, "api/Dockerfile COPY", api_copied, api_mounted)
    compare(problems, "worker/Dockerfile COPY", worker_copied, worker_mounted)

    entrypoint = (ROOT / "api" / "entrypoint.sh").read_text()
    reload_dirs = re.search(r'^RELOAD_DIRS="(?P<dirs>[^"]*)"', entrypoint, re.MULTILINE)
    compare(
        problems,
        "api/entrypoint.sh RELOAD_DIRS",
        set(reload_dirs["dirs"].split()) if reload_dirs else set(),
        api_mounted,
    )

    for problem in problems:
        sys.stderr.write(f"{problem}\n")
    if problems:
        sys.stderr.write(
            "The Makefile's PACKAGES and the compose &api-volumes and "
            "&worker-volumes lists are the reference.\n"
        )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
