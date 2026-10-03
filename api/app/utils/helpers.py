from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.config import DEFAULT_ADMIN_PASSWORD, settings
from app.core.database import async_db_session
from app.core.security import hash_password
from app.utils.validation import MIN_PASSWORD_LENGTH
from shared.logging import get_logger
from shared.models.user import User

logger = get_logger(__name__)

ADMIN_SEED_REFUSED = (
    "ADMIN_PASSWORD must be set to at least {length} characters, not the default, "
    "before the first start."
)


def check_admin_password() -> None:
    """Refuse to seed the first admin with the default or a short password."""
    password = settings.ADMIN_PASSWORD
    if settings.DEBUG:
        return
    if password == DEFAULT_ADMIN_PASSWORD or len(password) < MIN_PASSWORD_LENGTH:
        raise RuntimeError(ADMIN_SEED_REFUSED.format(length=MIN_PASSWORD_LENGTH))


async def create_initial_admin() -> None:
    async with async_db_session() as session:
        result = await session.execute(select(User).limit(1))
        existing_user = result.scalar_one_or_none()

        if existing_user is None:
            check_admin_password()
            admin = User(
                email=settings.ADMIN_EMAIL,
                username=settings.ADMIN_USERNAME,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                is_superuser=True,
            )
            session.add(admin)
            # another api process can win the same first boot
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                return
            logger.info(f"Initial admin created: {settings.ADMIN_USERNAME}")
