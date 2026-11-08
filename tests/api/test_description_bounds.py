from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from shared.models import interest, project, proxy, scan_context, scan_engine

pytestmark = pytest.mark.api

_ENDPOINT = {"scheme": "http", "host": "192.0.2.1", "port": 8080}
_DISMISS = {"host": "www.example.com", "target_id": uuid.uuid4()}

CASES = [
    (
        scan_context.ScanContextCreate,
        {"name": "c"},
        "description",
        scan_context.MAX_DESCRIPTION,
    ),
    (scan_context.ScanContextUpdate, {}, "description", scan_context.MAX_DESCRIPTION),
    (
        scan_engine.ScanEngineCreate,
        {"name": "e"},
        "description",
        scan_context.MAX_DESCRIPTION,
    ),
    (scan_engine.ScanEngineUpdate, {}, "description", scan_context.MAX_DESCRIPTION),
    (project.ProjectCreate, {"name": "p"}, "description", project.MAX_DESCRIPTION),
    (project.ProjectCreate, {"name": "p"}, "label", project.MAX_LABEL),
    (
        proxy.ProxyCreate,
        {"name": "x", "endpoints": [_ENDPOINT]},
        "description",
        proxy.MAX_DESCRIPTION,
    ),
    (proxy.ProxyUpdate, {}, "description", proxy.MAX_DESCRIPTION),
    (
        interest.InterestRuleCreate,
        {"name": "r", "kind": "k"},
        "description",
        interest.MAX_DESCRIPTION,
    ),
    (interest.InterestRuleUpdate, {}, "description", interest.MAX_DESCRIPTION),
    (interest.InterestRuleUpdate, {}, "name", interest.MAX_RULE_NAME),
    (interest.DismissRequest, _DISMISS, "note", interest.MAX_NOTE),
    (interest.DismissRequest, _DISMISS, "kind", interest.MAX_KIND),
]


@pytest.mark.parametrize(("model", "base", "field", "cap"), CASES)
def test_a_field_takes_its_column_width_and_no_more(model, base, field, cap):
    assert getattr(model(**base, **{field: "a" * cap}), field) == "a" * cap
    with pytest.raises(ValidationError):
        model(**base, **{field: "a" * (cap + 1)})
