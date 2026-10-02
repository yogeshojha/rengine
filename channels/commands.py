"""Every command a chat answers to, spelled from the tool registries."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field, replace
from functools import lru_cache
from typing import Any

from mcp import registry as mcp_registry
from mcp.capabilities import Capability
from shared.definitions.channels import (
    CHAT_GROUP_ORDER,
    COMMAND_GROUPS,
    COMMAND_PRESETS,
    ChatGroup,
    CommandSource,
)
from toolbox import registry as toolbox_registry


class CommandError(ValueError):
    """The text could not be bound to a command."""


BUILTIN: dict[str, tuple[str, str]] = {
    "start": ("Start", "Pair this chat, or show its status once paired."),
    "help": ("Help", "The command list, or the usage of one command."),
    "project": ("Project", "Show or switch the selected project."),
    "projects": ("Projects", "The projects this account can select."),
    "whoami": ("Who am I", "This chat's account, project and capabilities."),
    "unpair": ("Unpair", "Remove this chat's access."),
}

_ARRAY = "array"
_INTEGER = "integer"
_NUMBER = "number"
_BOOLEAN = "boolean"
_STRING = "string"
_TRUE = frozenset({"true", "yes", "on", "1"})
_FALSE = frozenset({"false", "no", "off", "0"})
_APOSTROPHE = re.compile(r"(?<=\w)'(?=\w)")


@dataclass(frozen=True)
class CommandSpec:
    name: str
    tool: str | None
    source: str
    title: str
    description: str
    capability: str
    touches_target: bool
    value_field: str
    presets: dict[str, Any] = field(default_factory=dict)
    schema: dict = field(default_factory=dict)
    group: str = ChatGroup.CHAT.value
    takes_args: bool = True

    @property
    def builtin(self) -> bool:
        return self.source == CommandSource.BUILTIN.value

    @property
    def steps_up(self) -> bool:
        return self.capability != Capability.READ.value

    @property
    def properties(self) -> dict[str, dict]:
        if not self.takes_args:
            return {}
        return {
            k: v
            for k, v in (self.schema.get("properties") or {}).items()
            if k not in self.presets
        }

    @property
    def required(self) -> list[str]:
        return [k for k in (self.schema.get("required") or []) if k not in self.presets]

    @property
    def usage(self) -> str:
        parts = [f"/{self.name}"]
        if self.value_field and self.value_field in self.properties:
            parts.append(f"<{self.value_field}>")
        others = [k for k in self.properties if k != self.value_field]
        if others:
            parts.append("[key=value]")
        return " ".join(parts)

    def args(self) -> list[dict]:
        required = set(self.required)
        out = []
        for name, prop in self.properties.items():
            out.append(
                {
                    "name": name,
                    "type": _type_label(prop),
                    "required": name in required,
                    "description": str(prop.get("description") or ""),
                    "default": _default_label(prop),
                    "options": _options(prop),
                }
            )
        return out


def normalise_name(raw: str) -> str:
    name = raw.strip().lstrip("/").split("@", 1)[0]
    return name.lower().replace("-", "").replace("_", "")


def _group_of(name: str, source: str) -> str:
    for group, names in COMMAND_GROUPS.items():
        if name in names:
            return group
    if source == CommandSource.TOOLBOX.value:
        return ChatGroup.LOOKUPS.value
    msg = f"/{name} is in no chat group. Add it to COMMAND_GROUPS."
    raise mcp_registry.ToolRegistrationError(msg)


@lru_cache(maxsize=1)
def catalog() -> dict[str, CommandSpec]:
    specs: dict[str, CommandSpec] = {}

    for name, (title, description) in BUILTIN.items():
        _add(
            specs,
            CommandSpec(
                name=name,
                tool=None,
                source=CommandSource.BUILTIN.value,
                title=title,
                description=description,
                capability=Capability.READ.value,
                touches_target=False,
                value_field="",
            ),
        )

    for spec in mcp_registry.registry().values():
        if spec.command is None:
            continue
        _add(
            specs,
            CommandSpec(
                name=spec.command,
                tool=spec.name,
                source=CommandSource.MCP.value,
                title=spec.title,
                description=spec.description,
                capability=spec.capability,
                touches_target=spec.capability == Capability.LAUNCH.value,
                value_field=spec.value_field,
                schema=spec.schema,
            ),
        )

    for spec in toolbox_registry.registry().values():
        _add(
            specs,
            CommandSpec(
                name=spec.command,
                tool=spec.name,
                source=CommandSource.TOOLBOX.value,
                title=spec.title,
                description=spec.description,
                capability=(
                    Capability.LAUNCH.value
                    if spec.touches_target
                    else Capability.READ.value
                ),
                touches_target=spec.touches_target,
                value_field=spec.value_field,
                schema=spec.tool_cls.schema(),
            ),
        )

    for preset in COMMAND_PRESETS:
        base = mcp_registry.get(preset.tool)
        if base is None:
            msg = f"Preset /{preset.name} names unknown tool {preset.tool!r}."
            raise mcp_registry.ToolRegistrationError(msg)
        _add(
            specs,
            CommandSpec(
                name=preset.name,
                tool=base.name,
                source=CommandSource.MCP.value,
                title=preset.title,
                description=preset.description,
                capability=base.capability,
                touches_target=base.capability == Capability.LAUNCH.value,
                value_field=base.value_field,
                presets=dict(preset.args),
                schema=base.schema,
                takes_args=preset.takes_args,
            ),
        )

    for name, spec in list(specs.items()):
        specs[name] = replace(spec, group=_group_of(name, spec.source))
    return specs


def _add(specs: dict[str, CommandSpec], spec: CommandSpec) -> None:
    if spec.name in specs:
        msg = f"/{spec.name} is declared twice ({specs[spec.name].source}, {spec.source})."
        raise mcp_registry.ToolRegistrationError(msg)
    if not mcp_registry.COMMAND_RE.match(spec.name):
        msg = f"/{spec.name} is not one short word."
        raise mcp_registry.ToolRegistrationError(msg)
    specs[spec.name] = spec


def get(name: str) -> CommandSpec | None:
    return catalog().get(normalise_name(name))


@lru_cache(maxsize=1)
def by_tool() -> dict[str, CommandSpec]:
    """The first chat command bound to each tool, preset-free ones first."""
    out: dict[str, CommandSpec] = {}
    for spec in sorted(catalog().values(), key=lambda s: bool(s.presets)):
        if spec.tool and spec.tool not in out:
            out[spec.tool] = spec
    return out


def by_group() -> list[tuple[str, list[CommandSpec]]]:
    """Commands grouped in declared group and command order."""
    grouped: dict[str, list[CommandSpec]] = {}
    for spec in catalog().values():
        grouped.setdefault(spec.group, []).append(spec)

    def position(spec: CommandSpec) -> tuple[int, str]:
        listed = COMMAND_GROUPS.get(spec.group, ())
        return (
            listed.index(spec.name) if spec.name in listed else len(listed),
            spec.name,
        )

    return [
        (g, sorted(grouped[g], key=position)) for g in CHAT_GROUP_ORDER if g in grouped
    ]


# ---------- parsing ----------


@dataclass
class Parsed:
    name: str
    bare: list[str]
    kwargs: dict[str, str]
    raw: str


def parse(text: str) -> Parsed | None:
    """None when the text is not a command."""
    raw = text.strip()
    if not raw.startswith("/"):
        return None
    try:
        tokens = _split(raw)
    except ValueError as exc:
        msg = "Unbalanced quote."
        raise CommandError(msg) from exc
    if not tokens:
        return None
    name = normalise_name(tokens[0])
    if not name:
        return None
    bare: list[str] = []
    kwargs: dict[str, str] = {}
    for token in tokens[1:]:
        key, sep, value = token.partition("=")
        plain_key = key.replace("_", "").replace("-", "")
        if sep and key and plain_key.isalnum() and not key[0].isdigit():
            kwargs[key.lower().replace("-", "_")] = value
        else:
            bare.append(token)
    return Parsed(name=name, bare=bare, kwargs=kwargs, raw=raw)


def _split(raw: str) -> list[str]:
    try:
        return shlex.split(raw, posix=True)
    except ValueError:
        return shlex.split(_APOSTROPHE.sub(r"\\'", raw), posix=True)


def bind(spec: CommandSpec, parsed: Parsed) -> dict[str, Any]:
    """Turn a parsed command into the tool's arguments."""
    properties = spec.properties
    args: dict[str, Any] = dict(spec.presets)
    if not spec.takes_args and (parsed.bare or parsed.kwargs):
        msg = f"/{spec.name} takes no arguments."
        raise CommandError(msg)

    for key, value in parsed.kwargs.items():
        if key in spec.presets:
            msg = f"{key} is set by /{spec.name}."
            raise CommandError(msg)
        if key not in properties:
            known = ", ".join(properties) or "none"
            msg = f"/{spec.name} has no argument {key}. Arguments: {known}."
            raise CommandError(msg)
        args[key] = _coerce(key, properties[key], value)

    if parsed.bare:
        if not spec.value_field or spec.value_field not in properties:
            msg = f"/{spec.name} takes key=value arguments only. Usage: {spec.usage}"
            raise CommandError(msg)
        if spec.value_field in args:
            msg = f"{spec.value_field} was given twice."
            raise CommandError(msg)
        prop = properties[spec.value_field]
        if _kind(prop) == _ARRAY:
            args[spec.value_field] = _coerce(spec.value_field, prop, parsed.bare)
        elif len(parsed.bare) > 1:
            msg = (
                f"/{spec.name} takes one value. Use key=value for the rest. "
                f"Usage: {spec.usage}"
            )
            raise CommandError(msg)
        else:
            args[spec.value_field] = _coerce(spec.value_field, prop, parsed.bare[0])

    missing = [k for k in spec.required if k not in args]
    if missing:
        msg = f"Missing {', '.join(missing)}. Usage: {spec.usage}"
        raise CommandError(msg)
    return args


def _kind(prop: dict) -> str:
    kind = prop.get("type")
    if isinstance(kind, str):
        return kind
    for option in prop.get("anyOf") or []:
        inner = option.get("type")
        if isinstance(inner, str) and inner != "null":
            return inner
    return _STRING


def _items(prop: dict) -> dict:
    if isinstance(prop.get("items"), dict):
        return prop["items"]
    for option in prop.get("anyOf") or []:
        if option.get("type") == _ARRAY and isinstance(option.get("items"), dict):
            return option["items"]
    return {}


def _coerce(name: str, prop: dict, raw: str | list[str]) -> Any:
    kind = _kind(prop)
    if kind == _ARRAY:
        values = raw if isinstance(raw, list) else _split_list(raw)
        item = _items(prop)
        return [_coerce(name, item, v) for v in values]
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    value = raw.strip()
    if kind == _INTEGER:
        try:
            return int(value)
        except ValueError as exc:
            msg = f"{name} must be a whole number."
            raise CommandError(msg) from exc
    if kind == _NUMBER:
        try:
            return float(value)
        except ValueError as exc:
            msg = f"{name} must be a number."
            raise CommandError(msg) from exc
    if kind == _BOOLEAN:
        lowered = value.lower()
        if lowered in _TRUE:
            return True
        if lowered in _FALSE:
            return False
        msg = f"{name} must be true or false."
        raise CommandError(msg)
    return value


def _split_list(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def _type_label(prop: dict) -> str:
    kind = _kind(prop)
    if kind == _ARRAY:
        return f"{_kind(_items(prop))}[]"
    return kind


def _default_label(prop: dict) -> str | None:
    value = prop.get("default")
    if value is None or value in ([], ""):
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _options(prop: dict) -> list[str]:
    if isinstance(prop.get("enum"), list):
        return [str(v) for v in prop["enum"]]
    for option in prop.get("anyOf") or []:
        if isinstance(option.get("enum"), list):
            return [str(v) for v in option["enum"]]
    return []
