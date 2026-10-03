from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from fastapi import HTTPException

from app.services.http_asset import HttpAssetService
from app.services.notification_channel import _server_moved
from app.services.proxy import _restore_passwords
from app.services.scan_context import _apply_extra_headers_update
from app.services.scan_engine.service import ScanEngineService
from app.services.scan_engine.validation import (
    _mask_tool_options,
    _unmask_tool_options,
    _without_secret_keys,
)
from reports.sections.findings_detail.section import _message
from shared.enums.api_key import APIProvider
from shared.enums.notification_channel import NotificationProvider
from shared.models.api_key import APIKey, APIKeyCreate, APIKeyUpdate
from shared.models.http_asset import HttpAsset
from shared.models.proxy import ProxyEndpoint
from shared.models.scan_context import AuthHeader, ScanContextUpdate
from shared.models.scan_engine import ScanEngineCreate, ScanEngineUpdate
from shared.services.api_key.async_api_key import APIKeyService
from shared.services.issue_tracking.body import mask_secrets
from shared.services.scan_resolve import (
    MASK,
    ResolvedScanConfig,
    _mask_headers,
    held_secrets,
    holding_secrets,
    redact_command,
    redact_message,
    redact_recorded,
    restore_masked_headers,
    run_secrets,
    scrub_error,
)
from shared.utils.crypto import try_decrypt
from tools.httpx.parser import parse_httpx_record
from tools.naabu.client import proxy_args

pytestmark = pytest.mark.api

CANARY = "SECRETCANARY7f3a91"


def _config(**fields) -> ResolvedScanConfig:
    return ResolvedScanConfig(
        target_value="example.com", target_type="domain", **fields
    )


# ---------- D1 recorded commands ----------


def test_the_naabu_proxy_password_never_reaches_a_recorded_command():
    proxy = f"socks5://alice:{CANARY}@10.0.0.5:1080"
    args, reason = proxy_args(proxy)
    assert reason is None
    command = "naabu -host example.com " + " ".join(args)
    assert CANARY not in redact_command(command)
    secrets = run_secrets(_config(proxy_url=proxy))
    assert CANARY not in redact_recorded(
        f"dial alice:{CANARY}@10.0.0.5 refused", secrets
    )


def test_run_secrets_carry_headers_proxy_and_tool_argument_values():
    config = _config(
        headers={"Authorization": f"Bearer {CANARY}1", "X-Auth": f"{CANARY}2"},
        proxy_url=f"http://bob:{CANARY}3@proxy:3128",
        tool_options={"nuclei": f"-var apikey={CANARY}4 -itoken {CANARY}5"},
    )
    secrets = run_secrets(config)
    for n in range(1, 6):
        assert f"{CANARY}{n}" in secrets
    assert secrets == sorted(secrets, key=len, reverse=True)


# ---------- D2 headers masked by value ----------


def test_every_context_header_value_is_masked_on_read():
    shown = _mask_headers(
        [{"name": "X-Auth", "value": CANARY}, {"name": "X", "value": ""}]
    )
    assert shown == [{"name": "X-Auth", "value": MASK}, {"name": "X", "value": ""}]


def test_a_masked_context_header_keeps_the_stored_value_whatever_its_name():
    stored = [
        {"name": "X-Auth", "value": CANARY},
        {"name": "X-Env", "value": "staging"},
    ]
    ctx = SimpleNamespace(extra_headers=stored)
    shown = [AuthHeader(**h) for h in _mask_headers(stored)]
    _apply_extra_headers_update(ctx, ScanContextUpdate(extra_headers=shown))
    assert ctx.extra_headers == stored


def test_a_masked_header_with_no_stored_value_is_refused():
    with pytest.raises(HTTPException) as refused:
        restore_masked_headers([{"name": "X-New", "value": MASK}], [])
    assert refused.value.status_code == 400


# ---------- engines: D2, D3, D9 ----------


async def _engine(durable_estate) -> tuple[ScanEngineService, uuid.UUID]:
    svc = ScanEngineService(durable_estate.session)
    created = await svc.create(
        durable_estate.project_id,
        durable_estate.user_id,
        ScanEngineCreate(
            name="Keyed",
            global_headers=[f"X-Auth: {CANARY}", "X-Env: staging"],
            tool_options={
                "nuclei": f"-var apikey={CANARY}a --header=Authorization:{CANARY}b",
                "subfinder": f"-auth {CANARY}c",
            },
            yaml_source=f"name: Keyed\ntool_options:\n  nuclei: -itoken {CANARY}d\n",
        ),
        superuser=True,
    )
    return svc, created.id


async def test_a_member_reads_no_engine_secret(durable_estate):
    svc, engine_id = await _engine(durable_estate)
    pid = durable_estate.project_id
    read = await svc.get(engine_id, pid)
    listed = await svc.list(pid)
    exported = await svc.export_yaml(engine_id, pid)
    copy = await svc.duplicate(engine_id, pid, durable_estate.user_id)
    for shown in (read.model_dump_json(), listed[0].model_dump_json(), exported):
        assert CANARY not in shown
        assert "staging" not in shown
    assert read.tool_options == {"nuclei": MASK, "subfinder": MASK}
    assert read.global_headers == [f"X-Auth: {MASK}", f"X-Env: {MASK}"]
    assert CANARY not in copy.model_dump_json()


async def test_an_administrator_reads_tool_args_redacted(durable_estate):
    svc, engine_id = await _engine(durable_estate)
    read = await svc.get(engine_id, durable_estate.project_id, superuser=True)
    assert CANARY not in read.model_dump_json()
    assert read.tool_options["nuclei"].startswith("-var apikey=")


async def test_a_member_saving_masked_tool_args_keeps_them(durable_estate):
    svc, engine_id = await _engine(durable_estate)
    pid = durable_estate.project_id
    shown = await svc.get(engine_id, pid)
    await svc.update(
        engine_id,
        pid,
        ScanEngineUpdate(
            name="Renamed",
            tool_options=shown.tool_options,
            global_headers=shown.global_headers,
        ),
    )
    stored = await svc._get_or_404(engine_id, pid)
    assert stored.tool_options["subfinder"] == f"-auth {CANARY}c"
    assert stored.global_headers == [f"X-Auth: {CANARY}", "X-Env: staging"]


async def test_engine_headers_and_tool_args_are_sealed_at_rest(durable_estate):
    _, engine_id = await _engine(durable_estate)
    row = (
        await durable_estate.session.execute(
            sa.text(
                "SELECT global_headers, tool_options, yaml_source "
                "FROM scan_engines WHERE id = :id"
            ),
            {"id": engine_id},
        )
    ).one()
    assert CANARY not in row.global_headers
    assert CANARY not in row.tool_options
    assert CANARY in try_decrypt(row.tool_options)
    assert CANARY not in (row.yaml_source or "")


def test_tool_options_never_survive_in_the_stored_document():
    source = "name: x\ntool_options: {nuclei: -itoken abc}\nstages: {}\n"
    assert "tool_options" not in _without_secret_keys(source)
    assert _without_secret_keys("name: x\n") == "name: x\n"


@pytest.mark.parametrize(
    "args",
    [
        f"-var apikey={CANARY}",
        f"--header=Authorization:{CANARY}",
        f'-header="X-Auth: {CANARY}"',
        f"-auth {CANARY}",
        f"--token={CANARY}",
        f"-u admin:{CANARY}",
        f"--user=admin:{CANARY}",
        f"-proxy-auth alice:{CANARY}",
    ],
)
def test_every_credential_spelling_is_redacted_and_round_trips(args):
    stored = {"nuclei": args}
    shown = _mask_tool_options(stored, superuser=True)
    assert CANARY not in shown["nuclei"]
    assert _unmask_tool_options(shown, stored) == stored


@pytest.mark.parametrize(
    "command",
    [
        "ffuf -w /tmp/w.txt:FUZZ -u https://a/FUZZ -maxtime 60",
        "nuclei -u example.com:8443 -rl 10",
        "naabu -passive -host example.com",
    ],
)
def test_a_target_or_a_switch_is_not_a_credential(command):
    assert redact_command(command) == command


# ---------- D4 probe requests ----------


def test_the_probe_request_masks_every_header_the_run_sent():
    config = _config(
        headers={
            "X-Auth": f"{CANARY}1",
            "X-Api-Auth": f"{CANARY}2",
            "Authentication": "v",
        }
    )
    request = (
        "GET /?echo=" + f"{CANARY}1" + " HTTP/1.1\r\nHost: example.com\r\n"
        f"X-Auth: {CANARY}1\r\nX-Api-Auth: {CANARY}2\r\nAuthentication: v\r\n"
        "User-Agent: probe\r\n\r\n"
    )
    with holding_secrets(config):
        fields = parse_httpx_record({"url": "https://example.com", "request": request})
    stored = fields["raw_request"]
    assert CANARY not in stored
    assert "Authentication: " + MASK in stored
    assert "User-Agent: probe" in stored
    assert parse_httpx_record({"request": f"GET / HTTP/1.1\r\nX-Other: {CANARY}"})[
        "raw_request"
    ].endswith(CANARY)


def test_a_stored_probe_request_is_masked_on_read_by_the_run_header_names():
    asset = HttpAsset(
        scan_id=uuid.uuid4(),
        target_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        url="https://example.com",
        host="example.com",
        raw_request=f"GET / HTTP/1.1\r\nHost: example.com\r\nX-Custom: {CANARY}\r\n\r\n",
    )
    detail = HttpAssetService(None)._to_detail(asset, None, ["X-Custom"])
    assert CANARY not in detail.raw_request


# ---------- D5 report evidence and failure text ----------


def test_report_evidence_masks_headers_and_provider_keys():
    request = (
        "POST /v1?api_key=QK123 HTTP/1.1\r\nAuthorization: Bearer abc\r\n\r\n"
        "key=sk-proj-AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"
    )
    shown = _message(request)
    assert "abc" not in shown
    assert "QK123" not in shown
    assert "sk-proj-" not in shown


def test_a_stage_failure_keeps_no_query_key_header_or_run_value():
    text = (
        f"HTTPError GET https://api.example/v1?apikey={CANARY}1 "
        f"{{'Authorization': 'Bearer {CANARY}2'}} sent {CANARY}3"
    )
    scrubbed = scrub_error(text, [f"{CANARY}3"])
    assert CANARY not in scrubbed
    assert "https://api.example/v1?" in scrubbed


# ---------- D6 generic maskers ----------


@pytest.mark.parametrize(
    "name",
    [
        "X-Authorization",
        "Authentication",
        "X-Auth",
        "X-Auth-User-Key",
        "X-Api-Auth",
        "X-Hub-Signature-256",
        "X-Jwt-Assertion",
        "X-Client-Secret",
        "X-Refresh-Token",
        "X-Api-Key",
    ],
)
def test_a_credential_header_name_is_masked_in_a_message(name):
    raw = f"GET / HTTP/1.1\r\nHost: x\r\n{name}: {CANARY}\r\n\r\n"
    assert CANARY not in redact_message(raw)


def test_folded_and_indented_header_lines_are_masked():
    raw = (
        f"GET / HTTP/1.1\r\nAuthorization: Bearer\r\n {CANARY}\r\n"
        f"  Cookie: sid={CANARY}\r\nX-Env: staging\r\n\r\n"
    )
    shown = redact_message(raw)
    assert CANARY not in shown
    assert "X-Env: staging" in shown


@pytest.mark.parametrize(
    "param", ["access_token", "api_key", "apikey", "token", "key", "secret", "sig"]
)
def test_a_credential_query_parameter_in_the_request_line_is_masked(param):
    raw = f"GET /x?page=2&{param}={CANARY} HTTP/1.1\r\nHost: x\r\n\r\n"
    shown = redact_message(raw)
    assert CANARY not in shown
    assert "page=2" in shown


@pytest.mark.parametrize(
    "key",
    [
        "sk-proj-AbCdEfGhIjKlMnOpQrStUvWxYz0123456789_-AbCdEf",
        "sk-AbCdEfGhIjKlMnOpQrStUvWxYz0123456789AbCdEfGh",
        "gsk_AbCdEfGhIjKlMnOpQrStUvWxYz0123456789AbCdEfGhIjKl",
        "xai-AbCdEfGhIjKlMnOpQrStUvWxYz0123456789AbCdEfGhIjKl",
        "sk_test_AbCdEfGhIjKlMnOpQrSt",
    ],
)
def test_provider_keys_are_masked(key):
    assert key not in mask_secrets(f"config = {{\n  provider: {key}\n}}")


def test_a_commit_hash_is_left_alone_and_lines_are_kept():
    text = "commit 3f8b2d6c1a94e0b7d5c2a9f1e3b4c6d8e0f2a4b6\nsk-AbCdEfGhIjKlMnOpQrStUvWxYz012\n"
    shown = mask_secrets(text, keep_lines=True)
    assert "3f8b2d6c1a94e0b7d5c2a9f1e3b4c6d8e0f2a4b6" in shown
    assert shown.count("\n") == text.count("\n")


# ---------- D7 destinations ----------


def test_a_proxy_password_does_not_follow_a_scheme_or_port_change():
    stored = [
        ProxyEndpoint(scheme="http", host="p", port=3128, username="u", password="pw")
    ]
    same = ProxyEndpoint(
        scheme="http", host="p", port=3128, username="u", password=MASK
    )
    assert _restore_passwords([same], stored)[0].password == "pw"
    for moved in (
        same.model_copy(update={"scheme": "socks5"}),
        same.model_copy(update={"port": 8080}),
    ):
        with pytest.raises(HTTPException) as refused:
            _restore_passwords([moved], stored)
        assert refused.value.status_code == 400


def test_turning_tls_off_is_a_server_change():
    stored = {"smtp_host": "mail", "smtp_port": 587, "username": "u", "use_tls": True}
    email = NotificationProvider.EMAIL.value
    assert _server_moved(email, stored, {**stored, "use_tls": False})
    assert not _server_moved(email, stored, dict(stored))


# ---------- D8 API keys ----------


async def test_an_api_key_never_stores_a_masked_value(durable_estate):
    svc = APIKeyService(durable_estate.session)
    with pytest.raises(HTTPException) as refused:
        await svc.create_key(APIKeyCreate(provider=APIProvider.CHAOS, key_value=MASK))
    assert refused.value.status_code == 400
    created = await svc.create_key(
        APIKeyCreate(provider=APIProvider.CHAOS, key_value=CANARY)
    )
    await svc.update_key(str(created.id), APIKeyUpdate(key_value=f"xx{MASK}"))
    row = await durable_estate.session.get(APIKey, created.id)
    assert try_decrypt(row.key_value) == CANARY


def test_scanners_redact_every_secret_the_run_holds():
    config = _config(
        headers={"X-Auth": "SECRETCANARYHDR0001"},
        proxy_url="socks5://alice:SECRETCANARYPXY0002@127.0.0.1:1080",
    )
    with holding_secrets(config):
        held = held_secrets(["SECRETCANARYEXTRA03", "short"])
    assert "SECRETCANARYPXY0002" in held
    assert "SECRETCANARYHDR0001" in held
    assert "SECRETCANARYEXTRA03" in held
    assert "short" not in held
