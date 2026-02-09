import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.enums.api_key import APIProvider
from shared.utils.datetime import utc_now

API_PROVIDER_META: dict[str, dict] = {
    APIProvider.VIEWDNS: {
        "name": "ViewDNS.info",
        "description": "Used for DNS intelligence, reverse lookups and DNS history",
        "docs_url": "https://viewdns.info/api/?src=reNgine",
    }
}


class APIKey(SQLModel, table=True):
    __tablename__ = "api_keys"
    __table_args__ = (UniqueConstraint("provider", name="uq_api_key_provider"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    provider: APIProvider = Field(index=True)
    key_value: str = Field(max_length=500)
    is_enabled: bool = Field(default=True)
    usage_counter: int = Field(default=0)
    last_used_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class APIKeyCreate(BaseModel):
    provider: APIProvider
    key_value: str


class APIKeyUpdate(BaseModel):
    key_value: str | None = None
    is_enabled: bool | None = None


class APIKeyRead(BaseModel):
    id: uuid.UUID
    provider: APIProvider
    key_value_masked: str
    is_enabled: bool
    usage_counter: int
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime
    meta: dict


class ProviderInfo(BaseModel):
    provider: APIProvider
    name: str
    description: str
    docs_url: str
    configured: bool = False
    is_enabled: bool = False
