"""Setup snippets for the MCP clients the connect flow names."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from mcp.settings import SERVER_NAME


@dataclass(frozen=True)
class ClientSpec:
    key: str
    label: str
    where: str
    lang: str
    render: Callable[[str, str], str]


def _json(body: dict) -> str:
    return json.dumps(body, indent=2)


def _bearer(secret: str) -> str:
    return f"Bearer {secret}"


def _claude_code(url: str, secret: str) -> str:
    return (
        f"claude mcp add --transport http {SERVER_NAME} {url} "
        f'--header "Authorization: {_bearer(secret)}"'
    )


def _claude_desktop(url: str, secret: str) -> str:
    return _json(
        {
            "mcpServers": {
                SERVER_NAME: {
                    "command": "npx",
                    "args": [
                        "-y",
                        "mcp-remote",
                        url,
                        "--header",
                        "Authorization:${RENGINE_AUTH}",
                    ],
                    "env": {"RENGINE_AUTH": _bearer(secret)},
                }
            }
        }
    )


def _cursor(url: str, secret: str) -> str:
    return _json(
        {
            "mcpServers": {
                SERVER_NAME: {"url": url, "headers": {"Authorization": _bearer(secret)}}
            }
        }
    )


def _vscode(url: str, secret: str) -> str:
    return _json(
        {
            "servers": {
                SERVER_NAME: {
                    "type": "http",
                    "url": url,
                    "headers": {"Authorization": _bearer(secret)},
                }
            }
        }
    )


def _generic(url: str, secret: str) -> str:
    return _json(
        {
            "mcpServers": {
                SERVER_NAME: {
                    "type": "http",
                    "url": url,
                    "headers": {"Authorization": _bearer(secret)},
                }
            }
        }
    )


CLIENTS: tuple[ClientSpec, ...] = (
    ClientSpec("claude_code", "Claude Code", "Terminal", "shell", _claude_code),
    ClientSpec(
        "claude_desktop",
        "Claude Desktop",
        "claude_desktop_config.json",
        "json",
        _claude_desktop,
    ),
    ClientSpec("cursor", "Cursor", "~/.cursor/mcp.json", "json", _cursor),
    ClientSpec("vscode", "VS Code", ".vscode/mcp.json", "json", _vscode),
    ClientSpec("other", "Other", "MCP configuration", "json", _generic),
)


def catalog() -> list[dict]:
    return [{"key": c.key, "label": c.label} for c in CLIENTS]


def snippets(url: str, secret: str) -> list[dict]:
    return [
        {
            "key": c.key,
            "label": c.label,
            "where": c.where,
            "lang": c.lang,
            "text": c.render(url, secret),
        }
        for c in CLIENTS
    ]
