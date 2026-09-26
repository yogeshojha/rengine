"""The bot token never leaves the box, and a chat cannot outrun its account."""

from __future__ import annotations

import uuid

import pytest

from channels import pairing, settings, stepup
from channels.identity import effective_capabilities, identity_for
from channels.models import ChannelChat
from channels.telegram import driver
from mcp.capabilities import Capability
from shared.definitions.channels import PAIRING_ALPHABET, PAIRING_CODE_LENGTH
from shared.models.user import User
from shared.services.scan_resolve import MASK

pytestmark = pytest.mark.channels

TOKEN = "1234567890:AAFxYz0123456789abcdefghijklmnopqrst"


def test_a_masked_token_keeps_only_the_public_bot_id():
    masked = settings.mask_secret(TOKEN)
    assert masked == f"1234567890:{MASK}"
    assert "AAF" not in masked


def test_redact_strips_the_token_from_any_text():
    assert TOKEN not in settings.redact(
        f"https://api.telegram.org/bot{TOKEN}/getMe", TOKEN
    )


def test_token_shape_is_checked_before_it_is_stored():
    assert driver.valid_token(TOKEN)
    assert not driver.valid_token("not-a-token")
    assert not driver.valid_token("")


def test_a_pairing_code_is_unambiguous_and_short():
    code = pairing.new_code()
    body = code.replace("-", "")
    assert len(body) == PAIRING_CODE_LENGTH
    assert all(c in PAIRING_ALPHABET for c in body)
    for ambiguous in "0O1I":
        assert ambiguous not in PAIRING_ALPHABET


def test_a_typed_code_is_normalised():
    assert pairing.normalise("h7k2 q9xz") == "H7K2-Q9XZ"
    assert pairing.normalise("H7K2-Q9XZ") == "H7K2-Q9XZ"


def test_only_an_authenticator_code_is_treated_as_one():
    assert stepup.looks_like_code("482913")
    assert stepup.looks_like_code("ab12-cd34")
    assert not stepup.looks_like_code("/scan_target 482913")
    assert not stepup.looks_like_code("48291")


def _chat(capabilities: list[str]) -> ChannelChat:
    return ChannelChat(
        channel="telegram",
        external_id="1",
        display="@op",
        user_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        capabilities=capabilities,
    )


def _user(*, totp: bool) -> User:
    return User(
        id=uuid.uuid4(),
        username="op",
        email="op@test.local",
        hashed_password="x",
        totp_enabled=totp,
    )


def test_no_authenticator_means_read_only():
    ceiling = {c.value: True for c in Capability}
    chat = _chat(["read", "plan", "write", "launch"])
    assert effective_capabilities(chat, _user(totp=False), ceiling) == ["read"]
    assert effective_capabilities(chat, None, ceiling) == ["read"]
    assert set(effective_capabilities(chat, _user(totp=True), ceiling)) == {
        "read",
        "plan",
        "write",
        "launch",
    }


def test_the_ceiling_caps_a_chat_below_what_it_was_granted():
    ceiling = {"read": True, "plan": True, "write": False, "launch": False}
    chat = _chat(["read", "plan", "write", "launch"])
    identity = identity_for(chat, _user(totp=True), ceiling)
    assert identity.capabilities == frozenset({"read", "plan"})
    assert identity.project_id == chat.project_id
    assert identity.name == "telegram:@op"
