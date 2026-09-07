"""One page shape for every list endpoint, with a bound the database can honour."""

from fastapi import Query
from fastapi_pagination import Page as _Page
from fastapi_pagination import Params
from fastapi_pagination.customization import CustomizedPage, UseParams

# a page beyond this multiplies out to an offset Postgres refuses, which surfaced
# as a 500 rather than an empty page
MAX_PAGE = 100_000


class BoundedParams(Params):
    page: int = Query(default=1, ge=1, le=MAX_PAGE, description="Page number")


Page = CustomizedPage[_Page, UseParams(BoundedParams)]
