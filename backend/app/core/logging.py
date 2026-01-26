from shared.logging import setup_logging

from app.config import settings

logger = setup_logging(
    name="rengine.backend",
    level=settings.LOG_LEVEL if hasattr(settings, "LOG_LEVEL") else "INFO",
    colored=True,
)
