"""The compiler moved to shared/ so the worker can compile a query too; this keeps the import path."""

import importlib
import pkgutil
import sys

import shared.services.asset_query as _pkg
from shared.services.asset_query import *
from shared.services.asset_query import __all__ as _all

for _info in pkgutil.iter_modules(_pkg.__path__):
    _module = importlib.import_module(f"{_pkg.__name__}.{_info.name}")
    sys.modules[f"{__name__}.{_info.name}"] = _module
    globals()[_info.name] = _module

__all__ = list(_all)
