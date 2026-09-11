"""A zone that transfers is both a source of names and a finding in its own right."""

from __future__ import annotations

import pytest

from shared.definitions.vulnerabilities import Scanner, Severity
from shared.enums.subdomain import SubdomainSource
from stages.zone_transfer.stage import ZoneTransferStage, _finding, transferred_names
from tools.dnsx.parser import parse_dnsx_record

pytestmark = pytest.mark.pipeline


def _line(owner: str, rtype: str, rdata: str, ttl: int = 7200) -> str:
    return f"{owner}\t{ttl}\tIN\t{rtype}\t{rdata}"


def _record(lines: list[str] | None, host: str = "example.com") -> dict:
    """dnsx answers every -axfr query with an object; only a transfer carries a chain."""
    axfr: dict = {"host": host}
    if lines is not None:
        axfr["chain"] = [{"host": host, "resolver": ["198.51.100.4:53"], "all": lines}]
    return {"host": host, "status_code": "NOERROR", "axfr": axfr}


_ZONE = [
    _line("example.com.", "SOA", "ns1.example.com. root.example.com. 1 2 3 4 5"),
    _line("example.com.", "NS", "ns1.example.com."),
    _line("example.com.", "A", "203.0.113.10"),
    _line("internal.example.com.", "A", "10.0.0.5"),
    _line("vpn.example.com.", "A", "203.0.113.11"),
    _line("www.example.com.", "CNAME", "edge.example.net."),
    _line("example.com.", "MX", "10 mail.example.com."),
]


# ── the parser used to throw a successful transfer away ──


def test_a_refused_transfer_is_not_a_transfer():
    parsed = parse_dnsx_record(_record(None))
    assert parsed.zone_transferred is False
    assert parsed.zone_names == set()


def test_a_successful_transfer_survives_parsing():
    """The object dnsx returns was discarded, so an open zone could never be reported."""
    parsed = parse_dnsx_record(_record(_ZONE))
    assert parsed.zone_transferred is True
    assert "internal.example.com" in parsed.zone_names


def test_an_empty_chain_is_a_refusal():
    parsed = parse_dnsx_record(_record([]))
    assert parsed.zone_transferred is False


def test_it_names_the_server_that_answered():
    parsed = parse_dnsx_record(_record(_ZONE))
    assert parsed.axfr is not None
    assert parsed.axfr.servers == ["198.51.100.4"]


# ── what a zone line yields ──


def test_every_record_owner_is_a_name():
    names = parse_dnsx_record(_record(_ZONE)).zone_names
    assert {"example.com", "internal.example.com", "vpn.example.com"} <= names


def test_a_name_a_record_points_at_is_a_name():
    """A CNAME or MX target is a host the zone named, even out of scope."""
    names = parse_dnsx_record(_record(_ZONE)).zone_names
    assert "edge.example.net" in names
    assert "mail.example.com" in names


def test_an_address_is_never_read_as_a_name():
    names = parse_dnsx_record(_record(_ZONE)).zone_names
    assert "203.0.113.10" not in names
    assert "10.0.0.5" not in names


def test_a_wildcard_owner_is_a_rule_not_a_host():
    lines = [_line("*.example.com.", "A", "203.0.113.12")]
    assert parse_dnsx_record(_record(lines)).zone_names == set()


def test_text_that_looks_like_a_record_type_is_not_parsed_as_one():
    """A TXT value may hold anything; only the type column decides."""
    lines = [_line("example.com.", "TXT", '"see NS evil.example.org for details"')]
    assert parse_dnsx_record(_record(lines)).zone_names == {"example.com"}


def test_a_malformed_line_is_skipped_rather_than_failing_the_run():
    lines = ["not a zone line at all", _line("ok.example.com.", "A", "203.0.113.1")]
    assert parse_dnsx_record(_record(lines)).zone_names == {"ok.example.com"}


def test_the_ledger_records_the_outcome_not_the_zone():
    """A row per name would make the DNS tab a second, capped copy of the inventory."""
    lines = [_line(f"h{i}.example.com.", "A", "203.0.113.1") for i in range(300)]
    parsed = parse_dnsx_record(_record(lines))
    assert len(parsed.zone_names) == 300
    rows = [r for r in parsed.to_db_records() if r["record_type"] == "AXFR"]
    assert len(rows) == 1
    assert rows[0]["value"] == "open · 300 names disclosed"


def test_the_ledger_counts_one_name_as_one():
    parsed = parse_dnsx_record(_record([_line("a.example.com.", "A", "203.0.113.1")]))
    rows = [r for r in parsed.to_db_records() if r["record_type"] == "AXFR"]
    assert rows[0]["value"] == "open · 1 name disclosed"


def test_a_refused_zone_writes_no_axfr_rows():
    rows = parse_dnsx_record(_record(None)).to_db_records()
    assert not [r for r in rows if r["record_type"] == "AXFR"]


# ── the finding ──


def test_the_finding_is_rengines_own_and_confirmed():
    found = _finding("example.com", ["internal.example.com", "vpn.example.com"])
    assert found.scanner == Scanner.RENGINE.value
    assert found.template_id == "rengine-zone-transfer"
    assert found.severity == Severity.HIGH.value


def test_the_finding_carries_the_count_and_a_sample():
    names = [f"h{i}.example.com" for i in range(25)]
    found = _finding("example.com", names)
    assert "25 hostnames" in found.description
    assert "h0.example.com" in found.description
    assert "15 more" in found.description


def test_one_name_reads_as_one_name():
    found = _finding("example.com", ["only.example.com"])
    assert "1 hostname came back" in found.description


def test_the_fingerprint_is_per_zone_and_stable():
    """Triage keys on it, so the same zone next week is the same finding."""
    a = _finding("example.com", ["a.example.com"])
    b = _finding("example.com", ["a.example.com", "b.example.com"])
    c = _finding("other.com", ["a.other.com"])
    assert a.fingerprint == b.fingerprint, "a bigger zone is the same misconfiguration"
    assert a.fingerprint != c.fingerprint


def test_the_stage_sends_nothing_and_produces_findings():
    assert ZoneTransferStage.touches_target is False
    assert "vulnerabilities" in ZoneTransferStage.produces
    assert "subdomain_discovery" in ZoneTransferStage.depends_on


# ── the stage reads what discovery recorded ──


async def _names_from(estate, scan: str) -> list[str]:
    sid = estate.scans[scan]
    return await estate.session.run_sync(lambda s: transferred_names(s, sid))


async def test_only_the_transferred_names_are_read_back(estate, now):
    """The source list on the row is the record that the zone transferred."""
    await estate.scan("example.com", "run", at=now)
    await estate.hosts(
        "run",
        ["internal.example.com"],
        at=now,
        sources=[SubdomainSource.ZONE_TRANSFER.value],
    )
    await estate.hosts(
        "run",
        ["both.example.com"],
        at=now,
        sources=["subfinder", SubdomainSource.ZONE_TRANSFER.value],
    )
    await estate.hosts("run", ["www.example.com"], at=now, sources=["subfinder"])

    assert await _names_from(estate, "run") == [
        "both.example.com",
        "internal.example.com",
    ]


async def test_a_scan_with_no_transfer_reads_back_nothing(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.hosts("run", ["www.example.com"], at=now, sources=["subfinder"])

    assert await _names_from(estate, "run") == []
