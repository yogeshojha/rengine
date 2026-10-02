from __future__ import annotations

from datetime import UTC, date, datetime
from typing import ClassVar

import pytest

from shared.definitions.toolbox import RowAction
from shared.models.http_asset import HttpAsset
from toolbox.base import ToolContext, ToolError
from toolbox.estate import classify_domains
from toolbox.org_lookup import MAX_DOMAINS
from toolbox.tools import org_domains
from toolbox.tools.org_domains import OrgDomains
from tools.crtsh.client import CrtShClient, CrtShError
from tools.crtsh.models import ROW_LIMIT, CrtShOrganization, CrtShResult
from tools.ripestat.models import SearchASN
from tools.ripestat.service import RIPEStatLookupError, RIPEStatService
from tools.viewdns.client import ViewDNSRejectedError
from tools.viewdns.models import (
    ReverseWhoisMatch,
    ReverseWhoisResponse,
    ViewDNSCacheRead,
    ViewDNSLookupType,
)
from tools.viewdns.service import (
    ViewDNSKeyNotConfiguredError,
    ViewDNSLookupError,
    ViewDNSService,
)

NOW = datetime(2026, 9, 27, tzinfo=UTC)


def crt(*orgs: tuple[str, int, dict], certs: int | None = None, stored=None):
    organizations = [
        CrtShOrganization(name=name, certs=n, domains=domains)
        for name, n, domains in orgs
    ]
    return CrtShResult(
        certs=certs if certs is not None else sum(o.certs for o in organizations),
        organizations=organizations,
        stored_at=stored,
    )


def viewdns(*domains: str, cached: bool = False):
    matches = [
        ReverseWhoisMatch(
            domain=d, created_date=date(2015, 1, 1), registrar="MarkMonitor"
        )
        for d in domains
    ]
    return ViewDNSCacheRead(
        lookup_type=ViewDNSLookupType.REVERSE_WHOIS,
        query_value="q",
        result_count=len(matches),
        cached=cached,
        queried_at=NOW if cached else None,
        data=ReverseWhoisResponse(
            query="q", result_count=len(matches), matches=matches
        ),
    )


@pytest.fixture
def sources(monkeypatch):
    """Configurable fakes for the three sources; records what each was asked."""

    class Sources:
        crt = crt()
        crt_error: Exception | None = None
        asns: ClassVar[list[SearchASN]] = []
        asn_error: Exception | None = None
        registrations = viewdns()
        registrations_error: Exception | None = None
        registrant = ""
        asked: ClassVar[dict[str, list[str]]] = {
            "crt": [],
            "ripe": [],
            "viewdns": [],
            "whois": [],
        }

    state = Sources()

    async def fake_crt(self, organization):
        state.asked["crt"].append(organization)
        if state.crt_error:
            raise state.crt_error
        return state.crt

    async def fake_asns(self, query):
        state.asked["ripe"].append(query)
        if state.asn_error:
            raise state.asn_error
        return state.asns

    async def fake_viewdns(self, query):
        state.asked["viewdns"].append(query)
        if state.registrations_error:
            raise state.registrations_error
        return state.registrations

    async def fake_registrant(self, ctx, domain):
        state.asked["whois"].append(domain)
        return state.registrant

    monkeypatch.setattr(CrtShClient, "search_organization", fake_crt)
    monkeypatch.setattr(RIPEStatService, "search_asns", fake_asns)
    monkeypatch.setattr(ViewDNSService, "reverse_whois", fake_viewdns)
    monkeypatch.setattr(OrgDomains, "_registrant", fake_registrant)
    return state


def ctx(session=None, project_id=None):
    return ToolContext(session=session, project_id=project_id)


async def run(value, context=None):
    return await OrgDomains().run(
        context or ctx(), OrgDomains.Input(organization=value)
    )


def block(out, kind, title=None):
    return next(
        b for b in out.blocks if b.kind == kind and (title is None or b.title == title)
    )


def sources_facts(out):
    return {f.label: f.value for f in block(out, "facts", "Sources").facts}


def domains(out):
    return [row[0].value for row in block(out, "table").rows]


async def test_organization_keeps_only_certificates_naming_it(sources):
    sources.crt = crt(
        ("Uber Technologies, Inc.", 1440, {"uber.com": date(2026, 9, 1)}),
        ("UBER TECHNOLOGIES, INC.", 4, {"uberinternal.com": None}),
        ("Uberduck, LLC", 30, {"uberduck.ai": None}),
    )
    out = await run("Uber Technologies")
    assert domains(out) == ["uber.com", "uberinternal.com"]
    similar = block(out, "tags", "Other organizations on matching certificates")
    assert [t.value for t in similar.tags] == ["Uberduck, LLC"]
    assert similar.tags[0].lookup.tool == "org_domains"
    assert (
        "1,444 certificates naming this organization"
        in sources_facts(out)["Certificate transparency"]
    )


async def test_corroborated_domains_rank_first_and_are_marked(sources):
    sources.crt = crt(("Acme Corp", 3, {"both.com": None, "cert.com": None}))
    sources.registrations = viewdns("both.com", "reg.com")
    out = await run("Acme Corp")
    assert domains(out) == ["both.com", "cert.com", "reg.com"]
    first = block(out, "table").rows[0]
    assert first[1].value == "Certificate, Registration"
    assert first[2].value == "2015-01-01"
    assert first[2].note == "MarkMonitor"


async def test_table_offers_add_as_targets_for_every_new_row(sources):
    sources.crt = crt(("Acme", 2, {"a.com": None, "b.com": None}))
    out = await run("Acme")
    table = block(out, "table")
    assert table.action == RowAction.ADD_TARGETS.value
    assert table.keys == ["a.com", "b.com"]
    assert table.total == 2
    assert out.raw["domains"][0]["domain"] == "a.com"


async def test_email_asks_reverse_whois_only(sources):
    sources.registrations = viewdns("uber.com", "ubereats.com")
    out = await run("Hostmaster@Uber.com")
    assert sources.asked["viewdns"] == ["hostmaster@uber.com"]
    assert sources.asked["crt"] == []
    assert sources.asked["ripe"] == []
    facts = sources_facts(out)
    assert facts["Certificate transparency"] == "Not used for an email address"
    assert facts["Routing registry"] == "Not used for an email address"
    assert block(out, "hero").sub == "Registrant email"
    assert domains(out) == ["uber.com", "ubereats.com"]


async def test_domain_resolves_its_owner_from_whois(sources):
    sources.registrant = "GitHub, Inc."
    sources.crt = crt(
        ("GitHub, Inc.", 5, {"github.com": None, "githubassets.com": None})
    )
    out = await run("https://www.github.com/login")
    assert sources.asked["whois"] == ["github.com"]
    assert sources.asked["crt"] == ["GitHub, Inc."]
    hero = block(out, "hero")
    assert hero.headline == "GitHub, Inc."
    assert hero.sub == "Owner of github.com, read from WHOIS"
    assert "github.com" in domains(out)


async def test_domain_with_no_published_owner_is_refused(sources):
    sources.registrant = ""
    with pytest.raises(ToolError) as exc:
        await run("cloudflare.com")
    assert "owner of cloudflare.com is not published" in str(exc.value)
    assert sources.asked["crt"] == []


async def test_domain_owner_comes_from_certificates_scans_read(sources, estate):
    await estate.target("acme.com")
    sid = await estate.scan("acme.com", "s1", at=NOW)
    tid = estate.targets["acme.com"]
    rows = [
        ("www.acme.com", "*.acme.com", "CN=*.acme.com, O=Acme Holdings\\, Inc., C=US"),
        ("api.acme.com", "api.acme.com", "CN=api.acme.com, O=Acme Holdings\\, Inc."),
        ("vpn.acme.com", "Sophos", "CN=Sophos, O=OM Networks Pvt Ltd"),
    ]
    for host, cn, dn in rows:
        estate.session.add(
            HttpAsset(
                project_id=estate.project_id,
                scan_id=sid,
                target_id=tid,
                url=f"https://{host}",
                host=host,
                port=443,
                status_code=200,
                discovered_at=NOW,
                tls_subject_cn=cn,
                tls_subject_dn=dn,
            )
        )
    await estate.session.flush()
    sources.crt = crt(("Acme Holdings, Inc.", 2, {"acme.com": None, "acme.io": None}))

    out = await run("acme.com", ctx(estate.session, estate.project_id))
    assert sources.asked["whois"] == []
    hero = block(out, "hero")
    assert hero.headline == "Acme Holdings, Inc."
    assert hero.sub == "Owner of acme.com, read from 2 certificates in this project"
    status = {row[0].value: row[4] for row in block(out, "table").rows}
    assert status["acme.com"].value == "Target"
    assert status["acme.com"].href == f"/targets/{tid}"
    assert status["acme.io"].value == "New"
    table = block(out, "table")
    assert table.keys[domains(out).index("acme.com")] is None
    assert out.pivot is not None


async def test_targets_and_seen_rank_after_new(sources, estate):
    await estate.target("tracked.com")
    await estate.scan("tracked.com", "s1", at=NOW)
    await estate.hosts("s1", ["seen.com"], at=NOW)
    sources.crt = crt(
        ("Acme", 3, {"tracked.com": None, "seen.com": None, "new.com": None})
    )
    out = await run("Acme", ctx(estate.session, estate.project_id))
    assert domains(out) == ["new.com", "seen.com", "tracked.com"]
    marks = {m.label: m.note for m in block(out, "hero").marks}
    assert marks == {"New": "1", "Targets": "1", "Networks": "0"}


async def test_networks_need_the_exact_holder(sources):
    sources.crt = crt(("Uber Technologies, Inc.", 1, {"uber.com": None}))
    sources.asns = [
        SearchASN(asn=962, holder="UBERDUCK-ANYCAST - Uberduck, LLC"),
        SearchASN(asn=19934, holder="UBER-FREIGHT - Uber Freight US LLC"),
        SearchASN(asn=63086, holder="UBER-PROD - Uber Technologies, Inc"),
        SearchASN(asn=134135, holder="UBER-AP - Uber Technologies Inc."),
    ]
    out = await run("Uber Technologies")
    assert sources.asked["ripe"] == ["Uber Technologies", "Uber"]
    networks = block(out, "tags", "Networks")
    assert [t.value for t in networks.tags] == ["AS63086", "AS134135"]
    assert networks.tags[0].lookup.tool == "whois"


async def test_accented_names_are_also_searched_unaccented(sources):
    sources.crt = crt(("SOCIETE GENERALE", 4, {"societegenerale.com": None}))
    out = await run("Société Générale")
    assert sources.asked["crt"] == ["Société Générale", "Societe Generale"]
    assert domains(out) == ["societegenerale.com"]


async def test_capped_and_stored_answers_are_stated(sources):
    sources.crt = crt(("Acme", 5, {"acme.com": None}), certs=ROW_LIMIT, stored=NOW)
    sources.registrations = viewdns("acme.net", cached=True)
    out = await run("Acme")
    joined = " ".join(out.caveats)
    assert "limit of 10,000 certificates" in joined
    assert "stored at 2026-09-27" in joined
    assert "Reverse WHOIS answered from a result stored on 2026-09-27" in joined
    assert "not checked against a certificate" in joined
    assert len(out.caveats) == len(set(out.caveats))


async def test_one_failing_source_is_a_status_not_an_error(sources):
    sources.crt_error = CrtShError("crt.sh did not answer within 25 seconds.")
    sources.registrations = viewdns("acme.com")
    out = await run("Acme")
    facts = sources_facts(out)
    assert (
        facts["Certificate transparency"] == "crt.sh did not answer within 25 seconds."
    )
    assert domains(out) == ["acme.com"]


async def test_every_source_failing_is_an_error(sources):
    sources.crt_error = CrtShError("down")
    sources.asn_error = RIPEStatLookupError("down")
    sources.registrations_error = ViewDNSLookupError("down")
    with pytest.raises(ToolError) as exc:
        await run("Acme")
    assert "No source answered" in str(exc.value)


async def test_no_viewdns_key_is_a_status(sources):
    sources.registrations_error = ViewDNSKeyNotConfiguredError("no key")
    sources.crt = crt(("Acme", 1, {"acme.com": None}))
    out = await run("Acme")
    assert sources_facts(out)["Reverse WHOIS"] == (
        "Not queried. Add a ViewDNS.info key in Settings."
    )


async def test_a_refused_name_says_so(sources):
    error = ViewDNSLookupError("ViewDNS refused the query")
    error.__cause__ = ViewDNSRejectedError("HTTP 400")
    sources.registrations_error = error
    sources.crt = crt(("Uber", 1, {"uber.com": None}))
    out = await run("Uber")
    assert sources_facts(out)["Reverse WHOIS"].startswith("ViewDNS refused this name")


async def test_no_domains_is_an_empty_table_not_an_error(sources):
    out = await run("Nobody In Particular")
    assert block(out, "table").rows == []
    assert block(out, "table").empty == "No domains found"
    assert out.summary == "0 domains for Nobody In Particular"


async def test_more_domains_than_the_cap_are_truncated_and_said(sources, monkeypatch):
    monkeypatch.setattr(org_domains, "MAX_DOMAINS", 5)
    sources.crt = crt(("Acme", 9, {f"d{i}.com": None for i in range(9)}))
    out = await run("Acme")
    assert len(domains(out)) == 5
    assert "Showing 5 of 9 domains." in out.caveats
    assert MAX_DOMAINS >= 1000


@pytest.mark.parametrize(
    "value",
    ["8.8.8.8", "AS13335", "co.uk", "%", "Inc.", "Domains By Proxy, LLC", "", "a"],
)
async def test_refused_input_asks_no_source(sources, value):
    with pytest.raises(ToolError):
        await run(value)
    assert sources.asked == {"crt": [], "ripe": [], "viewdns": [], "whois": []}


async def test_summary_counts_new_and_networks(sources):
    sources.crt = crt(("IBM", 2, {"ibm.com": None, "ibm.net": None}))
    sources.asns = [SearchASN(asn=163, holder="IBM-RESEARCH-AS - IBM")]
    out = await run("IBM")
    assert out.summary == "2 domains for IBM · 2 new · 1 network"


async def test_classify_domains_without_project_is_empty():
    result = await classify_domains(None, None, ["example.com"])
    assert result.targets == {}
    assert result.seen == set()
