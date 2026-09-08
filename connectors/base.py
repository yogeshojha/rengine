"""One directory per connector, auto-discovered."""

from __future__ import annotations

from dataclasses import dataclass, field

from shared.definitions.connectors import SourceTool


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
    # where the client lives in this repository, when one exists
    source_path: str = ""
    # tools whose traffic this proxy labels, in the order the UI offers them
    tools: tuple[str, ...] = (SourceTool.PROXY.value, SourceTool.REPEATER.value)
    # this proxy can supply the session already in use
    supports_sessions: bool = True
    # scope can be pushed back into the proxy
    supports_scope_push: bool = False
    available: bool = True

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
            "tools": list(self.tools),
            "supports_sessions": self.supports_sessions,
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
