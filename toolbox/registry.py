"""Every discovered tool, validated once and described for the UI."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from functools import lru_cache

from shared.definitions.toolbox import (
    GROUP_HELP,
    GROUP_LABELS,
    GROUP_ORDER,
    ToolboxCatalog,
    ToolExecution,
    ToolField,
    ToolSpecRead,
)
from toolbox.base import Tool
from toolbox.tools import discover


class ToolRegistrationError(RuntimeError):
    """A tool module declares an invalid tool."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    title: str
    description: str
    group: str
    icon: str
    execution: str
    touches_target: bool
    placeholder: str
    examples: tuple[str, ...]
    tool_cls: type[Tool]

    @property
    def queued(self) -> bool:
        return self.execution == ToolExecution.QUEUED.value

    def read(self) -> ToolSpecRead:
        return ToolSpecRead(
            name=self.name,
            title=self.title,
            description=self.description,
            group=self.group,
            icon=self.icon,
            execution=self.execution,
            touches_target=self.touches_target,
            placeholder=self.placeholder,
            examples=list(self.examples),
            fields=_field_specs(self.tool_cls.schema()),
        )


_JSON_TYPES = {"integer", "number", "boolean", "string", "array"}


def _resolve(prop: dict, defs: dict) -> dict:
    ref = prop.get("$ref") or next(
        (m.get("$ref") for m in prop.get("allOf") or [] if isinstance(m, dict)), None
    )
    if not ref or not ref.startswith("#/$defs/"):
        return prop
    target = defs.get(ref.rsplit("/", 1)[-1])
    return {**target, **prop} if isinstance(target, dict) else prop


def _field_specs(schema: dict) -> list[ToolField]:
    defs = schema.get("$defs") or {}
    required = set(schema.get("required") or ())
    out: list[ToolField] = []
    for name, raw in (schema.get("properties") or {}).items():
        prop = _resolve(raw, defs)
        options = prop.get("options") or prop.get("enum")
        kind = prop.get("type")
        out.append(
            ToolField(
                name=name,
                title=prop.get("title") or name.replace("_", " ").capitalize(),
                description=prop.get("description") or None,
                type=kind if kind in _JSON_TYPES else "string",
                default=prop.get("default"),
                options=list(options) if options else None,
                option_labels=prop.get("option_labels") or None,
                minimum=prop.get("minimum"),
                maximum=prop.get("maximum"),
                required=name in required,
            )
        )
    return out


def _validate(cls: type[Tool]) -> None:
    for attribute in ("name", "title", "description", "Input"):
        if not getattr(cls, attribute, None):
            msg = f"{cls.__qualname__} must set `{attribute}`."
            raise ToolRegistrationError(msg)
    if cls.group not in GROUP_ORDER:
        msg = f"{cls.__qualname__} declares unknown group {cls.group!r}."
        raise ToolRegistrationError(msg)
    if cls.execution not in {e.value for e in ToolExecution}:
        msg = f"{cls.__qualname__} declares unknown execution {cls.execution!r}."
        raise ToolRegistrationError(msg)
    is_async = inspect.iscoroutinefunction(cls.run)
    wants_async = cls.execution == ToolExecution.INLINE.value
    if is_async != wants_async:
        msg = (
            f"{cls.__qualname__} declares execution={cls.execution!r} but its `run` is "
            f"{'async' if is_async else 'sync'}; inline runs on the api, queued on the worker."
        )
        raise ToolRegistrationError(msg)


@lru_cache(maxsize=1)
def registry() -> dict[str, ToolSpec]:
    specs: dict[str, ToolSpec] = {}
    for name, cls in sorted(discover().items()):
        _validate(cls)
        specs[name] = ToolSpec(
            name=name,
            title=cls.title,
            description=cls.description.strip(),
            group=cls.group,
            icon=cls.icon,
            execution=cls.execution,
            touches_target=bool(cls.touches_target),
            placeholder=cls.placeholder,
            examples=tuple(cls.examples),
            tool_cls=cls,
        )
    return specs


def get(name: str) -> ToolSpec | None:
    return registry().get(name)


def catalog() -> ToolboxCatalog:
    specs = sorted(
        registry().values(), key=lambda s: (GROUP_ORDER.index(s.group), s.title)
    )
    present = [g for g in GROUP_ORDER if any(s.group == g for s in specs)]
    return ToolboxCatalog(
        groups=[
            {"key": g, "label": GROUP_LABELS[g], "help": GROUP_HELP[g]} for g in present
        ],
        tools=[s.read() for s in specs],
    )
