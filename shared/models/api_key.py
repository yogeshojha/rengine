import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.enums.api_key import APIProvider
from shared.utils.datetime import utc_now

API_PROVIDER_META: dict[str, dict] = {
    APIProvider.VIEWDNS: {
        "name": "ViewDNS.info",
        "description": "DNS intelligence, reverse lookups and DNS history",
        "docs_url": "https://viewdns.info/api/?src=reNgine",
        "requires_username": False,
        "icon": "scan-search",
    },
    APIProvider.GITHUB: {
        "name": "GitHub",
        "description": "Subdomains found in public code, and subfinder's GitHub source",
        "docs_url": "https://github.com/settings/tokens",
        "requires_username": False,
        "icon": "github",
    },
    APIProvider.CHAOS: {
        "name": "Chaos",
        "description": "ProjectDiscovery Chaos subdomain dataset",
        "docs_url": "https://cloud.projectdiscovery.io",
        "requires_username": False,
        "icon": "radar",
    },
    APIProvider.NETLAS: {
        "name": "Netlas",
        "description": "Internet-wide asset and attack-surface intelligence",
        "docs_url": "https://netlas.io",
        "requires_username": False,
        "icon": "globe",
    },
    APIProvider.SECURITYTRAILS: {
        "name": "SecurityTrails",
        "description": "DNS, domain and subdomain history intelligence",
        "docs_url": "https://securitytrails.com",
        "requires_username": False,
        "icon": "route",
    },
    APIProvider.HACKERONE: {
        "name": "HackerOne",
        "description": "Program scope and reports from HackerOne",
        "docs_url": "https://api.hackerone.com",
        "requires_username": True,
        "icon": "shield",
    },
    APIProvider.INTIGRITI: {
        "name": "Intigriti",
        "description": "Program scope from Intigriti, including invite-only programs",
        "docs_url": "https://app.intigriti.com/researcher/personal-access-tokens",
        "requires_username": False,
        "icon": "shield",
    },
    APIProvider.VULNX: {
        "name": "vulnx",
        "description": "ProjectDiscovery vulnerability intelligence: exploits, coverage and exposure",
        "docs_url": "https://cloud.projectdiscovery.io",
        "requires_username": False,
        "icon": "biohazard",
    },
    APIProvider.INTERACTSH: {
        "name": "Interactsh",
        "description": "Auth token for a self-hosted out-of-band callback server",
        "docs_url": "https://github.com/projectdiscovery/interactsh",
        "requires_username": False,
        "icon": "satellite-dish",
    },
}


class APIKey(SQLModel, table=True):
    __tablename__ = "api_keys"
    __table_args__ = (UniqueConstraint("provider", name="uq_api_key_provider"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    provider: APIProvider = Field(index=True)
    key_value: str = Field(max_length=1000)
    key_meta: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    is_enabled: bool = Field(default=True)
    usage_counter: int = Field(default=0)
    last_used_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class APIKeyCreate(BaseModel):
    provider: APIProvider
    key_value: str
    key_meta: dict | None = None


class APIKeyUpdate(BaseModel):
    key_value: str | None = None
    is_enabled: bool | None = None
    key_meta: dict | None = None


class APIKeyRead(BaseModel):
    id: uuid.UUID
    provider: APIProvider
    key_value_masked: str
    key_meta: dict | None = None
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
    icon: str = "package"
    requires_username: bool = False
    configured: bool = False
    is_enabled: bool = False
