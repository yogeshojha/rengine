from starlette.requests import Request

UNKNOWN = "unknown"


def client_id(request: Request) -> str:
    """The peer uvicorn resolved through --forwarded-allow-ips."""
    return request.client.host if request.client else UNKNOWN
