from __future__ import annotations

import uuid

import pytest
from sqlalchemy import cast, delete, func, not_, or_, select, update
from sqlalchemy.dialects.postgresql import JSONB

from shared.definitions.rescan import SEED_SOURCES, SeedKind
from shared.enums.subdomain import SubdomainSource
from shared.enums.target import TargetType
from shared.models.subdomain import Subdomain
from shared.models.target import Target
from shared.models.target_seed import TargetSeed
from shared.services import target_seeds
from shared.services.scan_resolve import ResolvedScanConfig
from stages.asset_seed.stage import AssetSeedStage
from stages.base import StageContext

pytestmark = pytest.mark.pipeline


def _target(value: str, target_type: TargetType) -> Target:
    return Target(
        target_value=value,
        target_type=target_type,
        project_id=uuid.uuid4(),
        created_by=uuid.uuid4(),
    )


def _resolved() -> ResolvedScanConfig:
    return ResolvedScanConfig(target_value="example.com", target_type="domain")


def test_a_line_is_classified_by_its_own_shape():
    seeds, rejected = target_seeds.parse(
        ["www.example.com", "https://app.example.com/login"],
        _target("example.com", TargetType.DOMAIN),
    )

    assert rejected == []
    assert {(s.kind, s.value) for s in seeds} == {
        (SeedKind.HOST.value, "www.example.com"),
        (SeedKind.URL.value, "https://app.example.com/login"),
    }


@pytest.mark.parametrize(
    "raw",
    ["WWW.Example.com", "  www.example.com  ", "www.example.com.", "*.www.example.com"],
)
def test_one_host_is_stored_once_however_it_is_written(raw):
    seeds, _ = target_seeds.parse(
        [raw, "www.example.com"], _target("example.com", TargetType.DOMAIN)
    )

    assert [s.value for s in seeds] == ["www.example.com"]


def test_a_name_outside_the_apex_is_refused_by_name():
    _, rejected = target_seeds.parse(
        ["evil.co.uk"], _target("example.com", TargetType.DOMAIN)
    )

    assert [r.value for r in rejected] == ["evil.co.uk"]
    assert "example.com" in rejected[0].reason


def test_an_address_cannot_seed_a_domain():
    _, rejected = target_seeds.parse(
        ["10.0.0.1"], _target("example.com", TargetType.DOMAIN)
    )

    assert "host names and URLs" in rejected[0].reason


def test_a_range_takes_the_addresses_it_covers():
    seeds, rejected = target_seeds.parse(
        ["10.0.0.7", "10.1.0.7"], _target("10.0.0.0/24", TargetType.IP_RANGE)
    )

    assert [s.value for s in seeds] == ["10.0.0.7"]
    assert [r.value for r in rejected] == ["10.1.0.7"]


def test_a_line_that_is_not_an_asset_is_refused():
    _, rejected = target_seeds.parse(
        ["not a host", ""], _target("example.com", TargetType.DOMAIN)
    )

    assert [r.value for r in rejected] == ["not a host"]


def test_stored_assets_carry_the_imported_source():
    rows = [
        TargetSeed(
            target_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            kind=SeedKind.HOST.value,
            value="www.example.com",
        )
    ]

    assert target_seeds.as_assets(rows) == [
        {
            "kind": SeedKind.HOST.value,
            "value": "www.example.com",
            "source": SubdomainSource.IMPORTED.value,
        }
    ]


def test_stored_seeds_do_not_make_a_run_focused():
    resolved = _resolved()

    target_seeds.apply(
        resolved,
        [{"kind": SeedKind.HOST.value, "value": "www.example.com"}],
        seed_only=False,
    )

    assert resolved.seed_only is False
    assert resolved.stages["asset_seed"]["enabled"] is True


def test_a_rescan_stays_focused():
    resolved = _resolved()

    target_seeds.apply(
        resolved,
        [{"kind": SeedKind.HOST.value, "value": "www.example.com"}],
        seed_only=True,
    )

    assert resolved.seed_only is True


def test_a_run_with_no_seeds_leaves_the_stage_alone():
    resolved = _resolved()

    target_seeds.apply(resolved, [], seed_only=False)

    assert "asset_seed" not in resolved.stages
    assert resolved.seed_assets == []


async def test_a_discovery_rerun_keeps_the_rows_it_did_not_write(estate, now):
    await estate.scan("example.com", "run", at=now)
    scan_id = estate.scans["run"]
    await estate.hosts("run", ["found.example.com"], at=now, sources=["subfinder"])
    await estate.hosts(
        "run",
        ["seeded.example.com"],
        at=now,
        sources=[SubdomainSource.IMPORTED.value],
    )
    await estate.hosts("run", ["picked.example.com"], at=now, sources=["rescan"])

    seeded = or_(
        *[cast(Subdomain.sources, JSONB).contains([source]) for source in SEED_SOURCES]
    )
    await estate.session.execute(
        delete(Subdomain).where(Subdomain.scan_id == scan_id, not_(seeded))
    )

    rows = (
        await estate.session.execute(
            select(Subdomain.name).where(Subdomain.scan_id == scan_id)
        )
    ).scalars()
    assert sorted(rows) == ["picked.example.com", "seeded.example.com"]


async def test_a_seeded_host_carries_its_source_and_its_answer(estate, now):
    await estate.scan("example.com", "run", at=now)
    target_id = estate.targets["example.com"]

    def write(sync_session):
        stage = AssetSeedStage.__new__(AssetSeedStage)
        stage.session = sync_session
        stage.ctx = StageContext(
            scan_id=estate.scans["run"],
            target_id=target_id,
            project_id=estate.project_id,
            target_value="example.com",
            target_type=TargetType.DOMAIN.value,
            resolved=_resolved(),
        )
        stage._sources = {
            "www.example.com": SubdomainSource.IMPORTED.value,
            "dead.example.com": SubdomainSource.IMPORTED.value,
        }
        stored = stage._persist_hosts(
            ["dead.example.com", "www.example.com"],
            {},
            {"www.example.com": {"ips": ["203.0.113.10"], "cname": None}},
        )
        sync_session.commit()
        return stored

    assert await estate.session.run_sync(write) == 2

    rows = (
        await estate.session.execute(
            select(
                Subdomain.name,
                Subdomain.sources,
                Subdomain.resolved_ips,
                Subdomain.is_active,
            )
            .where(Subdomain.scan_id == estate.scans["run"])
            .order_by(Subdomain.name)
        )
    ).all()
    assert [(r[0], r[1], r[2], r[3]) for r in rows] == [
        ("dead.example.com", [SubdomainSource.IMPORTED.value], [], False),
        ("www.example.com", [SubdomainSource.IMPORTED.value], ["203.0.113.10"], True),
    ]


async def test_seeding_the_same_host_twice_updates_one_row(estate, now):
    await estate.scan("example.com", "run", at=now)

    def write(sync_session, answers):
        stage = AssetSeedStage.__new__(AssetSeedStage)
        stage.session = sync_session
        stage.ctx = StageContext(
            scan_id=estate.scans["run"],
            target_id=estate.targets["example.com"],
            project_id=estate.project_id,
            target_value="example.com",
            target_type=TargetType.DOMAIN.value,
            resolved=_resolved(),
        )
        stage._sources = {"www.example.com": SubdomainSource.IMPORTED.value}
        stage._persist_hosts(["www.example.com"], {}, answers)
        sync_session.commit()

    await estate.session.run_sync(lambda s: write(s, {}))
    await estate.session.run_sync(
        lambda s: write(
            s, {"www.example.com": {"ips": ["203.0.113.10"], "cname": None}}
        )
    )

    rows = (
        await estate.session.execute(
            select(Subdomain.resolved_ips, Subdomain.is_active).where(
                Subdomain.scan_id == estate.scans["run"]
            )
        )
    ).all()
    assert rows == [(["203.0.113.10"], True)]


def test_a_url_seed_counts_for_its_host():
    assets = [
        {"kind": SeedKind.URL.value, "value": "https://app.example.com/login"},
        {"kind": SeedKind.HOST.value, "value": "WWW.example.com"},
        {"kind": SeedKind.ADDRESS.value, "value": "203.0.113.10"},
    ]

    assert target_seeds.seeded_hosts(assets) == ["app.example.com", "www.example.com"]


def test_a_run_with_no_seeds_has_no_seeded_hosts():
    assert target_seeds.seeded_hosts(None) == []


def _seed_stage(monkeypatch, passes: list[dict[str, dict]]):
    """A stage whose dnsx passes are scripted, so the silent-drop retry is observable."""
    stage = AssetSeedStage.__new__(AssetSeedStage)
    stage._recovered = 0
    calls: list[list[str]] = []

    def query(hosts):
        calls.append(list(hosts))
        answer = passes.pop(0) if passes else {}
        return {h: a for h, a in answer.items() if h in hosts}, False

    stage._query = query
    return stage, calls


def test_a_name_the_first_pass_dropped_is_asked_again(monkeypatch):
    answer = {"ips": ["203.0.113.10"], "cname": None}
    stage, calls = _seed_stage(monkeypatch, [{}, {"www.example.com": answer}])

    answers, unanswered = stage._resolve(["www.example.com"])

    assert calls == [["www.example.com"], ["www.example.com"]]
    assert answers == {"www.example.com": answer}
    assert unanswered == 0
    assert stage._recovered == 1


def test_a_name_that_does_not_exist_is_not_a_drop(monkeypatch):
    stage, _calls = _seed_stage(monkeypatch, [{}, {}])

    answers, unanswered = stage._resolve(["gone.example.com"])

    assert answers == {}
    assert unanswered == 1
    assert stage._recovered == 0


def test_only_the_unanswered_names_are_asked_again(monkeypatch):
    answer = {"ips": ["203.0.113.10"], "cname": None}
    stage, calls = _seed_stage(monkeypatch, [{"a.example.com": answer}, {}])

    stage._resolve(["a.example.com", "b.example.com"])

    assert calls == [["a.example.com", "b.example.com"], ["b.example.com"]]


async def test_a_seed_write_stays_under_the_bind_parameter_cap(estate, now):
    await estate.scan("example.com", "run", at=now)
    names = [f"h{i}.example.com" for i in range(4000)]

    def write(sync_session):
        stage = AssetSeedStage.__new__(AssetSeedStage)
        stage.session = sync_session
        stage.ctx = StageContext(
            scan_id=estate.scans["run"],
            target_id=estate.targets["example.com"],
            project_id=estate.project_id,
            target_value="example.com",
            target_type=TargetType.DOMAIN.value,
            resolved=_resolved(),
        )
        stage._sources = dict.fromkeys(names, SubdomainSource.IMPORTED.value)
        stored = stage._persist_hosts(names, {}, {})
        sync_session.commit()
        return stored

    assert await estate.session.run_sync(write) == 4000
    count = await estate.session.scalar(
        select(func.count())
        .select_from(Subdomain)
        .where(Subdomain.scan_id == estate.scans["run"])
    )
    assert count == 4000


async def test_a_dropped_seed_never_overwrites_a_good_answer(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.hosts(
        "run", ["www.example.com"], at=now, ips=["203.0.113.10"], sources=["subfinder"]
    )
    await estate.session.execute(
        update(Subdomain)
        .where(Subdomain.scan_id == estate.scans["run"])
        .values(is_active=True)
    )

    def write(sync_session):
        stage = AssetSeedStage.__new__(AssetSeedStage)
        stage.session = sync_session
        stage.ctx = StageContext(
            scan_id=estate.scans["run"],
            target_id=estate.targets["example.com"],
            project_id=estate.project_id,
            target_value="example.com",
            target_type=TargetType.DOMAIN.value,
            resolved=_resolved(),
        )
        stage._sources = {"www.example.com": SubdomainSource.IMPORTED.value}
        stage._persist_hosts(["www.example.com"], {}, {})
        sync_session.commit()

    await estate.session.run_sync(write)

    row = (
        await estate.session.execute(
            select(Subdomain.resolved_ips, Subdomain.is_active).where(
                Subdomain.scan_id == estate.scans["run"]
            )
        )
    ).one()
    assert row == (["203.0.113.10"], True)


@pytest.mark.parametrize("raw", ["127.0.0.1", "169.254.1.1", "224.0.0.1", "::"])
def test_address_space_a_scan_never_aims_at_is_refused(raw):
    _, rejected = target_seeds.parse([raw], _target("AS13335", TargetType.ASN))

    assert [r.value for r in rejected] == [raw]


def test_an_asn_takes_a_public_address():
    seeds, rejected = target_seeds.parse(
        ["203.0.113.10"], _target("AS13335", TargetType.ASN)
    )

    assert rejected == []
    assert [s.value for s in seeds] == ["203.0.113.10"]
