"""Force every SQLModel datetime column to TIMESTAMPTZ (tz-aware).

Imported first in shared.models.__init__ so the patch is active before any table
class is defined. asyncpg requires the column type and the bound (tz-aware) value
to agree; with timezone=True the API binds `TIMESTAMP WITH TIME ZONE` and the API
serializes ISO-8601 UTC with offset (no client timezone drift).
"""

import sqlmodel.main as _sqlmodel_main
from sqlalchemy import DateTime as _SADateTime

_orig_get_sqlalchemy_type = _sqlmodel_main.get_sqlalchemy_type


def _get_sqlalchemy_type_tz(field):
    result = _orig_get_sqlalchemy_type(field)
    return _SADateTime(timezone=True) if result is _SADateTime else result


_sqlmodel_main.get_sqlalchemy_type = _get_sqlalchemy_type_tz
