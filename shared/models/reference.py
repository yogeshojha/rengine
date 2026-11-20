from typing import Any

from pydantic import BaseModel, Field

from shared.definitions.access_keys import AccessKeyLevel


class ReferenceParameter(BaseModel):
    name: str
    location: str
    required: bool = False
    type: str = "string"
    description: str | None = None


class ReferenceOperation(BaseModel):
    group: str
    method: str
    path: str
    summary: str
    access: AccessKeyLevel
    parameters: list[ReferenceParameter] = Field(default_factory=list)
    example: Any | None = None
    curl: str = ""


class ReferenceGroup(BaseModel):
    name: str
    operations: list[ReferenceOperation] = Field(default_factory=list)
