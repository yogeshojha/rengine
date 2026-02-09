"""Synchronous API key service for Celery workers.
Mirrors the subset of APIKeyService needed by background tasks:
"""

from sqlalchemy.orm import Session
from sqlmodel import select

from shared.enums.api_key import APIProvider
from shared.models.api_key import APIKey
from shared.utils.datetime import utc_now


class SyncAPIKeyService:
    def __init__(self, session: Session):
        self.session = session

    def get_key_for_provider(self, provider: APIProvider) -> str | None:
        """Get the raw key value for a provider."""
        result = self.session.execute(
            select(APIKey).where(
                APIKey.provider == provider,
                APIKey.is_enabled == True,  # noqa: E712
            )
        )
        api_key = result.scalar_one_or_none()
        if not api_key:
            return None
        return api_key.key_value

    def increment_usage(self, provider: APIProvider) -> None:
        """Increment usage counter after a successful API call."""
        result = self.session.execute(select(APIKey).where(APIKey.provider == provider))
        api_key = result.scalar_one_or_none()
        if api_key:
            api_key.usage_counter += 1
            api_key.last_used_at = utc_now()
            self.session.add(api_key)
            self.session.commit()

    def disable_key(self, provider: APIProvider) -> None:
        """Disable a key on rate limit or auth errors."""
        result = self.session.execute(select(APIKey).where(APIKey.provider == provider))
        api_key = result.scalar_one_or_none()
        if api_key:
            api_key.is_enabled = False
            api_key.updated_at = utc_now()
            self.session.add(api_key)
            self.session.commit()
