from app.config import settings
from shared.logging import setup_logging

logger = setup_logging(
    name="rengine.backend",
    level=settings.LOG_LEVEL if hasattr(settings, "LOG_LEVEL") else "INFO",
    colored=True,
)
