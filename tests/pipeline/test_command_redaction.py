from __future__ import annotations

import pytest

from shared.services.scan_resolve import (
    MASK,
    redact_command,
    redact_recorded,
    secret_runs,
)

pytestmark = pytest.mark.pipeline

_TOKEN = "eyJhbGciOiJIUzI1NiJ9.payload"


@pytest.mark.parametrize(
    "command",
    [
        f"httpx -l /tmp/t.txt -header Authorization: Bearer {_TOKEN} -silent",
        f"katana -list /tmp/t -header Authorization: Bearer {_TOKEN} -jsonl",
        f"nuclei -list /tmp/t -header Authorization: Bearer {_TOKEN} -jsonl",
        f"ffuf -w /tmp/w.txt:FUZZ -H Authorization: Bearer {_TOKEN} -mc 200",
        f'httpx -header "Authorization: Bearer {_TOKEN}" -silent',
        f"katana -headers Authorization: Bearer {_TOKEN} -jsonl",
    ],
)
def test_every_header_flag_the_tools_take_is_redacted(command: str):
    redacted = redact_command(command)
    assert _TOKEN not in redacted
    assert MASK in redacted


def test_a_header_name_outside_the_sensitive_list_is_redacted():
    redacted = redact_command("httpx -header X-Company-Session: s3cr3tvalue -silent")
    assert "s3cr3tvalue" not in redacted
    assert "X-Company-Session" in redacted


def test_the_flags_around_a_header_survive():
    redacted = redact_command(
        f"httpx -l /tmp/t.txt -header Cookie: sid={_TOKEN} -threads 150 -silent"
    )
    assert redacted.endswith("-threads 150 -silent")
    assert redacted.startswith("httpx -l /tmp/t.txt -header Cookie: ")


@pytest.mark.parametrize(
    "command",
    [
        "naabu -timeout 3s -top-ports 100",
        "ffuf -w /tmp/w.txt:FUZZ -u https://a/FUZZ -maxtime 60",
        "httpx -l /tmp/t.txt -threads 150 -silent",
    ],
)
def test_an_ordinary_flag_is_left_alone(command: str):
    assert redact_command(command) == command


def test_secret_runs_still_reads_back_what_was_masked():
    command = f"nuclei -header X-Api-Session: {_TOKEN} -header X-Other: plainvalue"
    assert secret_runs(command) == [_TOKEN, "plainvalue"]


def test_a_run_secret_is_masked_wherever_it_lands():
    recorded = redact_recorded(
        f"httpx -u https://a/?t={_TOKEN} -silent", secrets=[_TOKEN]
    )
    assert _TOKEN not in recorded
    assert MASK in recorded


def test_redact_recorded_handles_no_text_and_no_secrets():
    assert redact_recorded(None) == ""
    assert redact_recorded("naabu -top-ports 100") == "naabu -top-ports 100"
