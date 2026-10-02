from __future__ import annotations

import re
from pathlib import Path

import pytest

from shared.definitions.api_keys import (
    API_PROVIDER_META,
    PROVIDER_GROUP_LABELS,
    RECON_GROUPS,
)
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
