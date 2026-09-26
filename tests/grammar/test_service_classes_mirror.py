from __future__ import annotations

import pytest

from shared.definitions.ports import (
    PORT_SOURCE_LABELS,
    SCAN_POLICY_LABELS,
    SENSITIVE_PORTS,
    SERVICE_CLASS_LABELS,
    SERVICE_CLASS_ORDER,
    PortSource,
    ServiceClass,
)
from tests.grammar.ts_mirror import Mirror

pytestmark = pytest.mark.grammar


@pytest.fixture(scope="module")
def mirror() -> Mirror:
    return Mirror("service-classes.ts")


def test_the_frontend_mirror_carries_every_service_class(mirror: Mirror):
    classes = {c.value for c in ServiceClass}
    assert mirror.values("ServiceClass") == classes
    assert tuple(mirror.const("SERVICE_CLASS_ORDER")) == SERVICE_CLASS_ORDER
    assert mirror.labels("SERVICE_CLASS_LABELS") == SERVICE_CLASS_LABELS
    assert set(mirror.const("SERVICE_CLASS_ICONS")) == classes
    assert set(mirror.const("SERVICE_CLASS_FILL")) == classes


def test_the_frontend_mirror_carries_every_port_source(mirror: Mirror):
    sources = {s.value for s in PortSource}
    assert mirror.values("PortSource") == sources
    assert mirror.labels("PORT_SOURCE_LABELS") == PORT_SOURCE_LABELS
    assert set(mirror.labels("PORT_SOURCE_HELP")) == sources


def test_the_frontend_mirror_carries_the_scan_policies(mirror: Mirror):
    assert mirror.labels("SCAN_POLICY_LABELS") == SCAN_POLICY_LABELS


def test_the_frontend_mirror_carries_every_sensitive_port(mirror: Mirror):
    assert mirror.const("SENSITIVE_PORTS") == set(SENSITIVE_PORTS)
