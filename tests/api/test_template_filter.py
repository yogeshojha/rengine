from __future__ import annotations

import pytest
from pydantic import ValidationError

from shared.definitions.vulnerabilities import TEMPLATE_SET_KEYS
from shared.models.vuln_template import TemplateFilter

pytestmark = pytest.mark.api


def test_an_unknown_check_set_is_refused_at_the_body():
    with pytest.raises(ValidationError, match="Unknown check set"):
        TemplateFilter(sets=["not-a-set"])


def test_a_known_check_set_is_kept():
    key = next(iter(TEMPLATE_SET_KEYS))
    assert TemplateFilter(sets=[key]).sets == [key]
