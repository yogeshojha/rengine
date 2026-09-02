"""Force every SQLModel datetime column to TIMESTAMPTZ — asyncpg rejects a naive bind."""

import sqlmodel.main as _sqlmodel_main
from sqlalchemy import DateTime as _SADateTime

_orig_get_sqlalchemy_type = _sqlmodel_main.get_sqlalchemy_type


def _get_sqlalchemy_type_tz(field):
    result = _orig_get_sqlalchemy_type(field)
    return _SADateTime(timezone=True) if result is _SADateTime else result


_sqlmodel_main.get_sqlalchemy_type = _get_sqlalchemy_type_tz
