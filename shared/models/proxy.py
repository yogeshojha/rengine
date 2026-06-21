import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator
from sqlmodel import Field, SQLModel

from shared.enums.proxy import ProxyMode, ProxyProtocol
from shared.utils.datetime import utc_now
from shared.utils.validation import clean_name

PROXY_MODES = tuple(m.value for m in ProxyMode)
PROXY_SCHEMES = tuple(p.value for p in ProxyProtocol)


class ProxyEndpoint(BaseModel):
    scheme: str
    host: str
    port: int
    username: str | None = None
    password: str | None = None


class Proxy(SQLModel, table=True):
    __tablename__ = "proxies"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str = Field(max_length=120)
    description: str | None = Field(default=None, max_length=500)
    mode: str = Field(default="single")
    is_active: bool = Field(default=True)
    is_default: bool = Field(default=False)
    endpoints_encrypted: str
    endpoint_count: int = Field(default=0)
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_test_at: datetime | None = Field(default=None)
    last_test_ok: bool | None = Field(default=None)
    last_test_message: str | None = Field(default=None)


class ProxyEndpointRead(BaseModel):
    scheme: str
    host: str
    port: int
    username: str | None = None
    has_password: bool
    url_masked: str


class ProxyCreate(BaseModel):
    name: str
    description: str | None = None
    mode: str = "single"
    is_active: bool = True
    is_default: bool = False
    endpoints: list[ProxyEndpoint] = Field(min_length=1)

    _validate_name = field_validator("name")(clean_name)


class ProxyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    mode: str | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    endpoints: list[ProxyEndpoint] | None = None


class ProxyRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    mode: str
    is_active: bool
    is_default: bool
    endpoints: list[ProxyEndpointRead]
    endpoint_count: int
    created_at: datetime
    updated_at: datetime
    last_test_at: datetime | None
    last_test_ok: bool | None
    last_test_message: str | None


class ProxyTestResult(BaseModel):
    success: bool
    message: str
    latency_ms: int | None = None
