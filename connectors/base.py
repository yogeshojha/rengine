"""One directory per connector, auto-discovered."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

CLIENT_DIR = Path("/app/binaries")
_NUMBER = re.compile(r"\d+")


def release_key(name: str, pattern: str) -> tuple[tuple[int, ...], str]:
    """Orders client files by the release numbers their wildcard matched, then by name."""
    prefix, _, suffix = pattern.partition("*")
    core = name[len(prefix) : len(name) - len(suffix) if suffix else None]
    return tuple(int(part) for part in _NUMBER.findall(core)), name


@dataclass(frozen=True)
class SetupStep:
    title: str
    detail: str
    control: str | None = None


class ProxyConnector:
    """A proxy this instance can receive traffic from."""

    kind: str = ""
    title: str = ""
    short_title: str = ""
    client_pattern: str = ""

    @property
    def client_file(self) -> str:
        """The highest client release in the clients directory."""
        if not self.client_pattern:
            return ""
        names = [path.name for path in CLIENT_DIR.glob(self.client_pattern)]
        if not names:
            return ""
        return max(names, key=lambda name: release_key(name, self.client_pattern))

    def setup(self) -> list[SetupStep]:
        raise NotImplementedError

    def spec(self) -> dict:
        return {
            "kind": self.kind,
            "title": self.title,
            "short_title": self.short_title or self.title,
            "client_file": self.client_file,
            "steps": [asdict(step) for step in self.setup()],
        }
