from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from app.services.scan_engine.service import ScanEngineService
from shared.definitions.tools import (
    DENIED_FLAGS,
    SCAN_TOOLS,
    TOOL_NAMES,
    denied_flag,
    parse_tool_args,
)
from shared.enums.target import TargetType
from shared.models.project import Project
from shared.models.scan_engine import ScanEngineCreate, ScanEngineUpdate
from shared.models.user import User
from shared.services.scan_resolve import ResolvedScanConfig
from stages.subdomain.providers.base import ProviderContext
from stages.subdomain.providers.subfinder import SubfinderProvider

pytestmark = pytest.mark.api

_ARGS = {"nuclei": "-retries 2"}


async def _project(durable):
    uid = uuid.uuid4()
    pid = uuid.uuid4()
    durable.add(
        User(
            id=uid,
            username=f"t{uid.hex[:8]}",
            email=f"{uid.hex[:8]}@test.local",
            hashed_password="x",
            is_superuser=True,
        )
    )
    await durable.flush()
    durable.add(Project(id=pid, name="T", slug=f"t-{pid.hex[:8]}", created_by=uid))
    await durable.flush()
    return pid, uid


async def _engine_with_args(svc, pid, uid):
    return await svc.create(
        pid, uid, ScanEngineCreate(name="Args", tool_options=_ARGS), superuser=True
    )


async def test_a_member_cannot_create_an_engine_with_tool_args(durable):
    pid, uid = await _project(durable)
    with pytest.raises(HTTPException) as refused:
        await ScanEngineService(durable).create(
            pid, uid, ScanEngineCreate(name="Args", tool_options=_ARGS)
        )
    assert refused.value.status_code == 403


async def test_a_member_creates_an_engine_without_tool_args(durable):
    pid, uid = await _project(durable)
    created = await ScanEngineService(durable).create(
        pid, uid, ScanEngineCreate(name="Plain")
    )
    assert created.tool_options == {}


async def test_an_administrator_sets_tool_args(durable):
    pid, uid = await _project(durable)
    created = await _engine_with_args(ScanEngineService(durable), pid, uid)
    assert created.tool_options == _ARGS


async def test_a_member_cannot_change_tool_args(durable):
    pid, uid = await _project(durable)
    svc = ScanEngineService(durable)
    created = await _engine_with_args(svc, pid, uid)
    with pytest.raises(HTTPException) as refused:
        await svc.update(
            created.id, pid, ScanEngineUpdate(tool_options={"nuclei": "-retries 3"})
        )
    assert refused.value.status_code == 403
    assert (await svc.get(created.id, pid)).tool_options == _ARGS


async def test_a_member_saving_the_engine_resends_its_tool_args_unchanged(durable):
    pid, uid = await _project(durable)
    svc = ScanEngineService(durable)
    created = await _engine_with_args(svc, pid, uid)
    updated = await svc.update(
        created.id,
        pid,
        ScanEngineUpdate(name="Renamed", tool_options=created.tool_options),
    )
    assert updated.name == "Renamed"
    assert updated.tool_options == _ARGS


async def test_a_member_duplicates_an_engine_carrying_tool_args(durable):
    pid, uid = await _project(durable)
    svc = ScanEngineService(durable)
    created = await _engine_with_args(svc, pid, uid)
    copy = await svc.duplicate(created.id, pid, uid)
    assert copy.tool_options == created.tool_options


async def test_a_member_cannot_import_tool_args(durable):
    pid, uid = await _project(durable)
    document = "name: Imported\ntool_options:\n  nuclei: -retries 2\n"
    with pytest.raises(HTTPException) as refused:
        await ScanEngineService(durable).import_yaml(pid, uid, document)
    assert refused.value.status_code == 403


@pytest.mark.parametrize(
    ("tool", "value", "flag"),
    [
        ("nuclei", "-ev", "-ev"),
        ("nuclei", "-retries 2 --env-vars", "--env-vars"),
        ("nuclei", "-code -tags rce", "-code"),
        ("nuclei", "-turl=https://example.invalid/t.yaml", "-turl"),
        ("nuclei", "-elog /app/api/app/main.py", "-elog"),
        ("nuclei", "--o /tmp/x", "--o"),
        ("httpx", "-srd /app", "-srd"),
        ("katana", "-config /etc/passwd", "-config"),
        ("ffuf", "-debug-log=/tmp/x", "-debug-log"),
        ("ffuf", "-input-cmd 'id' -input-num 1", "-input-cmd"),
        ("ffuf", "--input-shell=/bin/sh", "--input-shell"),
        ("naabu", "-nmap-cli 'nmap -sV'", "-nmap-cli"),
        ("katana", "-ho --renderer-cmd-prefix=id", "-ho"),
        ("nuclei", "-headless -ho --renderer-cmd-prefix=id", "-ho"),
        ("nuclei", "-cdpe ws://127.0.0.1:9222", "-cdpe"),
        (
            "httpx",
            "-ss -headless-options=--renderer-cmd-prefix=id",
            "-headless-options",
        ),
        ("dnsx", "-output /app/stages/registry.py", "-output"),
        ("dnsx", "-ot '{{host}}'", "-ot"),
        ("dalfox", "--custom-payload /app/.env", "--custom-payload"),
        ("tlsx", "-ob /bin/sh", "-ob"),
        ("subfinder", "-oD /app", "-oD"),
        ("subfinder", "-pc /etc/passwd", "-pc"),
        ("alterx", "-config=/etc/passwd", "-config"),
        ("cdncheck", "-output /app/x", "-output"),
        ("urlfinder", "-od /app", "-od"),
        ("amass", "-scripts /tmp", "-scripts"),
        ("wafw00f", "--output=/app/x", "--output"),
        ("wafw00f", "--outp=/app/x", "--outp"),
        ("wafw00f", "-ao/app/x", "-ao/app/x"),
        ("dalfox", "--config /etc/passwd", "--config"),
        ("dalfox", "-So/app/x", "-So/app/x"),
        ("julius", "-qp/tmp", "-qp/tmp"),
    ],
)
async def test_an_administrator_cannot_set_a_denied_flag(durable, tool, value, flag):
    pid, uid = await _project(durable)
    with pytest.raises(HTTPException) as refused:
        await ScanEngineService(durable).create(
            pid,
            uid,
            ScanEngineCreate(name="Args", tool_options={tool: value}),
            superuser=True,
        )
    assert refused.value.status_code == 400
    assert refused.value.detail == f"{tool} does not take {flag}."


async def test_a_denied_flag_name_as_a_value_is_kept(durable):
    pid, uid = await _project(durable)
    created = await ScanEngineService(durable).create(
        pid,
        uid,
        ScanEngineCreate(name="Args", tool_options={"nuclei": "-tags code,config"}),
        superuser=True,
    )
    assert created.tool_options == {"nuclei": "-tags code,config"}


def test_a_stored_denied_flag_never_reaches_the_tool():
    resolved = ResolvedScanConfig(
        target_value="example.com",
        target_type=TargetType.DOMAIN.value,
        tool_options={"ffuf": "-input-cmd 'id' -input-num 1", "nuclei": "-retries 2"},
    )
    assert resolved.tool_args("ffuf") == []
    assert resolved.tool_args("nuclei") == ["-retries", "2"]


def test_a_tool_example_is_not_a_denied_flag():
    for spec in SCAN_TOOLS:
        assert denied_flag(spec.name, parse_tool_args(spec.example)) is None


def test_every_tool_that_takes_args_declares_its_denied_flags():
    assert set(DENIED_FLAGS) == TOOL_NAMES


def test_a_subdomain_provider_drops_a_denied_flag():
    provider = SubfinderProvider(
        ProviderContext(
            domain="example.com",
            timeout=60,
            threads=10,
            proxy_url=None,
            api_keys={},
            tool_options={"subfinder": "-all -pc /etc/passwd"},
        )
    )
    assert provider.extra_args == []
