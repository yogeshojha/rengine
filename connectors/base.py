"""One directory per connector, auto-discovered."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from shared.definitions.connectors import SourceTool

CLIENT_DIR = Path(os.environ.get("CLIENTS_DIR", "/app/binaries"))


@dataclass(frozen=True)
class SetupStep:
    title: str
    detail: str
    code: str | None = None
    lang: str | None = None


class ProxyConnector:
    """A proxy this instance can receive traffic from."""

    kind: str = ""
    title: str = ""
    vendor: str = ""
    description: str = ""
    docs_url: str = ""
    source_path: str = ""
    client_pattern: str = ""
    tools: tuple[str, ...] = (SourceTool.PROXY.value, SourceTool.REPEATER.value)
    supports_scope_push: bool = False
    available: bool = True

    @property
    def client_file(self) -> str:
        """The client build present in the clients directory."""
        if not self.client_pattern:
            return ""
        found = sorted(CLIENT_DIR.glob(self.client_pattern))
        return found[-1].name if found else ""

    def setup(self, *, endpoint: str, secret: str) -> list[SetupStep]:
        raise NotImplementedError

    def spec(self) -> dict:
        return {
            "kind": self.kind,
            "title": self.title,
            "vendor": self.vendor,
            "description": self.description,
            "docs_url": self.docs_url,
            "source_path": self.source_path,
            "client_file": self.client_file,
            "tools": list(self.tools),
            "supports_scope_push": self.supports_scope_push,
            "available": self.available,
        }


@dataclass
class ConnectorSpec:
    kind: str
    title: str
    connector: ProxyConnector
    order: int = 0
    tags: list[str] = field(default_factory=list)
