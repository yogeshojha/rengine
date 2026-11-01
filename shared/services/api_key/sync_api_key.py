from collections.abc import Iterable

from sqlalchemy.orm import Session
from sqlmodel import select

from shared.enums.api_key import APIProvider
from shared.logging import get_logger
from shared.models.api_key import APIKey
from shared.utils.crypto import SecretDecryptionError, decrypt_stored

logger = get_logger(__name__)


def open_key(row: APIKey) -> str | None:
    """The key's plain value, or None when this instance cannot open it."""
    try:
        return decrypt_stored(row.key_value, label="API key") or None
    except SecretDecryptionError:
        logger.warning("api key unreadable", provider=row.provider.value)
        return None


class SyncAPIKeyService:
    def __init__(self, session: Session):
        self.session = session

    def get_key_for_provider(self, provider: APIProvider) -> str | None:
        result = self.session.execute(
            select(APIKey).where(
                APIKey.provider == provider,
                APIKey.is_enabled.is_(True),
            )
        )
        api_key = result.scalar_one_or_none()
        if not api_key:
            return None
        return open_key(api_key)

    def credentials(
        self, providers: Iterable[APIProvider]
    ) -> dict[str, tuple[str, dict | None]]:
        """Each enabled, readable key among `providers`, with its key_meta."""
        wanted = list(dict.fromkeys(providers))
        if not wanted:
            return {}
        rows = self.session.execute(
            select(APIKey).where(
                APIKey.provider.in_(wanted),
                APIKey.is_enabled.is_(True),
            )
        ).scalars()
        out: dict[str, tuple[str, dict | None]] = {}
        for row in rows:
            key = open_key(row)
            if key:
                out[row.provider.value] = (key, row.key_meta)
        return out
