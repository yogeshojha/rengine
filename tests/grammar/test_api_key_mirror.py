from __future__ import annotations

import re
from pathlib import Path

import pytest

from shared.definitions.api_keys import (
    API_PROVIDER_META,
    PROVIDER_GROUP_LABELS,
    RECON_GROUPS,
    SUBFINDER_SOURCES,
)
from shared.definitions.discovery_sources import (
    NOTE_KEY,
    SOURCES_KEY,
    UNKEYED_KEY,
    SourceStatus,
)
from shared.definitions.ports import PASSIVE_PORT_SOURCES, PortSource
from shared.enums.api_key import APIProvider, ProviderGroup
from shared.services.notifier import SHARED_BOT_PROVIDER

pytestmark = pytest.mark.grammar

KEYS = Path("/app/frontend-config/api-keys.ts")
NOTIFICATIONS = Path("/app/frontend-config/notification-providers.ts")


def test_every_provider_sits_in_a_labelled_group():
    assert set(API_PROVIDER_META) == set(APIProvider)
    assert {meta["group"] for meta in API_PROVIDER_META.values()} <= set(
        PROVIDER_GROUP_LABELS
    )
    assert set(PROVIDER_GROUP_LABELS) == {g.value for g in ProviderGroup}


def test_provider_group_mirror():
    block = re.search(r"export enum ProviderGroup \{(.*?)\}", KEYS.read_text(), re.S)
    assert block, "ProviderGroup is missing from the mirror"
    assert set(re.findall(r"= '([^']+)'", block.group(1))) == {
        g.value for g in ProviderGroup
    }


def test_recon_groups_mirror():
    block = re.search(
        r"export const RECON_GROUPS[^=]*= \[(.*?)\];", KEYS.read_text(), re.S
    )
    assert block, "RECON_GROUPS is missing from the mirror"
    names = re.findall(r"ProviderGroup\.(\w+)", block.group(1))
    assert [ProviderGroup[name].value for name in names] == list(RECON_GROUPS)


def test_shared_bot_mirror():
    found = re.search(
        r"export const SHARED_BOT_PROVIDER: NotifProvider = '([^']+)';",
        NOTIFICATIONS.read_text(),
    )
    assert found, "SHARED_BOT_PROVIDER is missing from the mirror"
    assert found.group(1) == SHARED_BOT_PROVIDER


SOURCES = Path("/app/frontend-config/discovery-sources.ts")
SERVICES = Path("/app/frontend-config/service-classes.ts")


def test_discovery_source_mirror():
    text = SOURCES.read_text()
    block = re.search(r"export enum SourceStatus \{(.*?)\}", text, re.S)
    assert block, "SourceStatus is missing from the mirror"
    assert set(re.findall(r"= '([^']+)'", block.group(1))) == {
        s.value for s in SourceStatus
    }
    assert f"SOURCES_KEY = '{SOURCES_KEY}'" in text
    assert f"UNKEYED_KEY = '{UNKEYED_KEY}'" in text
    assert f"NOTE_KEY = '{NOTE_KEY}'" in text


def test_port_source_mirror():
    text = SERVICES.read_text()
    block = re.search(r"export enum PortSource \{(.*?)\}", text, re.S)
    assert block, "PortSource is missing from the mirror"
    assert set(re.findall(r"= '([^']+)'", block.group(1))) == {
        s.value for s in PortSource
    }
    passive = re.search(r"PASSIVE_PORT_SOURCES[^=]*= new Set\(\[(.*?)\]\)", text, re.S)
    assert passive, "PASSIVE_PORT_SOURCES is missing from the mirror"
    names = re.findall(r"PortSource\.(\w+)", passive.group(1))
    assert {PortSource[n].value for n in names} == PASSIVE_PORT_SOURCES
    for source in PortSource:
        assert re.search(rf"\b{source.value}: '", text), (
            f"{source.value} has no label or help"
        )


def test_every_subfinder_source_sits_in_a_recon_group():
    for provider in SUBFINDER_SOURCES:
        assert API_PROVIDER_META[provider]["group"] in RECON_GROUPS
