"""Remote control vocabulary: channels, chat states, command sources and the pairing gate."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from shared.enums.api_key import APIProvider


class ChannelKind(StrEnum):
    TELEGRAM = "telegram"


CHANNEL_ORDER: tuple[str, ...] = tuple(c.value for c in ChannelKind)

CHANNEL_LABELS: dict[str, str] = {
    ChannelKind.TELEGRAM.value: "Telegram",
}

# API key provider per channel
CHANNEL_PROVIDERS: dict[str, APIProvider] = {
    ChannelKind.TELEGRAM.value: APIProvider.TELEGRAM,
}


class ChatState(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    BLOCKED = "blocked"


CHAT_STATE_LABELS: dict[str, str] = {
    ChatState.ACTIVE.value: "Active",
    ChatState.REVOKED.value: "Revoked",
    ChatState.BLOCKED.value: "Blocked",
}


class CommandSource(StrEnum):
    MCP = "mcp"
    TOOLBOX = "toolbox"
    BUILTIN = "builtin"


COMMAND_SOURCE_ORDER: tuple[str, ...] = (
    CommandSource.BUILTIN.value,
    CommandSource.MCP.value,
    CommandSource.TOOLBOX.value,
)

COMMAND_SOURCE_LABELS: dict[str, str] = {
    CommandSource.BUILTIN.value: "Chat",
    CommandSource.MCP.value: "Tools",
    CommandSource.TOOLBOX.value: "Lookups",
}


class CommandPreset(BaseModel):
    """A command name bound to a tool with arguments already set."""

    name: str
    tool: str
    title: str
    description: str
    args: dict[str, object] = Field(default_factory=dict)
    takes_args: bool = True


COMMAND_PRESETS: tuple[CommandPreset, ...] = (
    CommandPreset(
        name="vulns",
        tool="query_assets",
        title="Findings",
        description="Findings on a target or across the selected project.",
        args={"dimension": "vulnerabilities"},
    ),
    CommandPreset(
        name="scans",
        tool="scan_status",
        title="Running scans",
        description="Scans running now.",
        takes_args=False,
    ),
)


class ChatGroup(StrEnum):
    TARGETS = "targets"
    SCANS = "scans"
    RESULTS = "results"
    LOOKUPS = "lookups"
    CHAT = "chat"


CHAT_GROUP_ORDER: tuple[str, ...] = tuple(g.value for g in ChatGroup)

CHAT_GROUP_LABELS: dict[str, str] = {
    ChatGroup.TARGETS.value: "Targets",
    ChatGroup.SCANS.value: "Scans",
    ChatGroup.RESULTS.value: "Results",
    ChatGroup.LOOKUPS.value: "Lookups",
    ChatGroup.CHAT.value: "Chat",
}

# chat group per command, toolbox lookups fall in LOOKUPS
COMMAND_GROUPS: dict[str, tuple[str, ...]] = {
    ChatGroup.TARGETS.value: ("targets", "target", "add"),
    ChatGroup.SCANS.value: ("scan", "scans", "progress", "pause", "resume", "cancel"),
    ChatGroup.RESULTS.value: ("vulns", "changes"),
    ChatGroup.CHAT.value: ("help", "start", "project", "projects", "whoami", "unpair"),
}

# ---------- pairing ----------

PAIRING_CODE_TTL = 600
PAIRING_CODE_LENGTH = 8
PAIRING_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
PENDING_PAIRINGS_MAX = 20

# ---------- step-up ----------

STEP_UP_GRACE_SECONDS = 900
STEP_UP_PENDING_SECONDS = 120
OTP_ATTEMPT_LIMIT = 5
OTP_ATTEMPT_WINDOW = 900

# ---------- limits ----------

DEFAULT_RATE_LIMIT = 60
MAX_CHATS = 50
MAX_DISPLAY = 120
MAX_EXTERNAL_ID = 64
STATUS_TTL = 30
