"""Field factories for the column shapes many tables repeat.

Each call builds a fresh `Column`, since SQLAlchemy binds a column to exactly one
table.
"""

from __future__ import annotations

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field


def json_list() -> Field:
    """A JSON array, never null, empty by default."""
    return Field(default_factory=list, sa_column=Column(JSON, nullable=False))


def json_dict() -> Field:
    """A JSON object, never null, empty by default."""
    return Field(default_factory=dict, sa_column=Column(JSON, nullable=False))


def nullable_text() -> Field:
    """Unbounded text that may be absent."""
    return Field(default=None, sa_column=Column(Text, nullable=True))
