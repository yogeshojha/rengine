"""Bounded page parameters for list endpoints."""

from fastapi import Query
from fastapi_pagination import Page as _Page
from fastapi_pagination import Params
from fastapi_pagination.customization import CustomizedPage, UseParams

MAX_PAGE = 100_000


class BoundedParams(Params):
    page: int = Query(default=1, ge=1, le=MAX_PAGE, description="Page number")


Page = CustomizedPage[_Page, UseParams(BoundedParams)]
