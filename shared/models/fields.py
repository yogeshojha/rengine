"""Field factories for JSON and Text columns."""

from typing import Any

from sqlalchemy import Column, Text
from sqlalchemy.types import JSON
from sqlmodel import Field


def json_list() -> Any:
    return Field(default_factory=list, sa_column=Column(JSON, nullable=False))


def json_dict() -> Any:
    return Field(default_factory=dict, sa_column=Column(JSON, nullable=False))


def optional_json_list() -> Any:
    return Field(default=None, sa_column=Column(JSON(none_as_null=True), nullable=True))


def text_column() -> Any:
    return Field(default=None, sa_column=Column(Text, nullable=True))
