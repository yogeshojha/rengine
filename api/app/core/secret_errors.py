"""Map a stored secret this instance cannot open to a 503."""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from shared.logging import get_logger
from shared.utils.crypto import SecretDecryptionError

logger = get_logger(__name__)


async def secret_decryption_handler(
    request: Request, exc: SecretDecryptionError
) -> JSONResponse:
    logger.error(
        "stored secret could not be decrypted",
        path=request.url.path,
        method=request.method,
    )
    return JSONResponse(
        status_code=HTTP_503_SERVICE_UNAVAILABLE, content={"detail": str(exc)}
    )
