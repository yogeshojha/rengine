from sqlmodel import select
from app.core.database import async_db_session
from app.models.user import User
from app.core.security import hash_password
from app.config import settings

async def create_initial_admin() -> None:
    """Create initial admin user if no users exist."""
    async with async_db_session() as session:
        result = await session.execute(select(User).limit(1))
        existing_user = result.scalar_one_or_none()
        
        if existing_user is None:
            admin = User(
                email=settings.ADMIN_EMAIL,
                username=settings.ADMIN_USERNAME,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                is_superuser=True,
            )
            session.add(admin)
            await session.commit()
            print(f"Initial admin created: {settings.ADMIN_USERNAME}")