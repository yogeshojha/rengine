from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from sqlalchemy.exc import DBAPIError

from app.api.router import router as api_router
from app.config import API_V1_PREFIX, settings
from app.core import ai_ledger
from app.core.body_limit import BodySizeLimitMiddleware
from app.core.database import check_capacity
from app.core.db_errors import data_exception_handler
from app.core.redis_sse_bridge import RedisSSEBridge
from app.core.sanitize import RejectNulMiddleware
from app.core.secret_errors import secret_decryption_handler
from app.core.throttle import GlobalRateLimitMiddleware
from app.core.validation_errors import validation_error_handler
from app.utils.helpers import create_initial_admin
from shared.config import APP_NAME, APP_VERSION
from shared.logging import get_logger, setup_logging
from shared.utils.crypto import SecretDecryptionError

setup_logging(level=settings.LOG_LEVEL)
logger = get_logger(__name__)
redis_sse_bridge = RedisSSEBridge(settings.redis_url)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting Backend...")
    try:
        ai_ledger.install()
        await create_initial_admin()
        await check_capacity()
        await redis_sse_bridge.start()
    except Exception as e:
        logger.exception("Failed to initialize the application: %s", e)
        raise e
    yield
    logger.info("Shutting down reNgine Backend...")
    await redis_sse_bridge.stop()


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    lifespan=lifespan,
)


add_pagination(app)

if "*" in settings.CORS_ORIGINS:
    msg = "CORS_ORIGINS must be an explicit allowlist (no '*') when credentials are enabled"
    raise ValueError(msg)

app.add_exception_handler(DBAPIError, data_exception_handler)
app.add_exception_handler(SecretDecryptionError, secret_decryption_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)

app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(GlobalRateLimitMiddleware)
app.add_middleware(RejectNulMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=API_V1_PREFIX)


@app.get("/")
async def root():
    return {
        "message": "reNgine API",
        "version": APP_VERSION,
        "docs": "/docs",
    }
