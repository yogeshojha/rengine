"""One directory per connector, auto-discovered."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

CLIENT_DIR = Path("/app/binaries")


@dataclass(frozen=True)
class SetupStep:
    title: str
    detail: str
    control: str | None = None


class ProxyConnector:
    """A proxy this instance can receive traffic from."""

    kind: str = ""
    title: str = ""
    client_pattern: str = ""

    @property
    def client_file(self) -> str:
        """The client build present in the clients directory."""
        if not self.client_pattern:
            return ""
        found = sorted(CLIENT_DIR.glob(self.client_pattern))
        return found[-1].name if found else ""

    def setup(self) -> list[SetupStep]:
        raise NotImplementedError

    def spec(self) -> dict:
        return {
            "kind": self.kind,
            "title": self.title,
            "client_file": self.client_file,
            "steps": [asdict(step) for step in self.setup()],
        }
