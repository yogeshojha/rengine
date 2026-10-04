from __future__ import annotations

import pytest

from app.services.infostealer import InfostealerService
from app.services.subdomain import SubdomainService
from shared.definitions.infostealer import Audience, HostStanding
from shared.enums.target import TargetType
from shared.models.infostealer import InfostealerLogin, TargetInfostealer
from shared.models.subdomain import SubdomainFilter
from shared.services.infostealer import lookup_domain
from tools.hudsonrock.parser import clean_login, parse_domain_report

pytestmark = pytest.mark.grammar

RICH = {
    "total": 44368,
    "totalStealers": 36647048,
    "employees": 308,
    "users": 42883,
    "third_parties": 1177,
    "logo": "https://cdn.brandfetch.io/example.com/fallback/lettermark",
    "totalUrls": 3561,
    "is_shopify": False,
    "last_employee_compromised": "2026-07-10T22:02:15.843Z",
    "last_user_compromised": "2026-10-01T17:55:33.390Z",
    "data": {
        "employees_urls": [
            {
                "occurrence": 246,
                "type": "Employee",
                "url": "https://vpn.example.com/vpn/index.html",
            },
            {
                "occurrence": 116,
                "type": "Employee",
                "url": "https://citrix.example.com/Citrix/XD76Web",
            },
            {
                "occurrence": 14,
                "type": "Employee",
                "url": "https://citrix.example.com/citrix/xd76web/",
            },
            {
                "occurrence": 7,
                "type": "Employee",
                "url": "https://portal.example.com/wps/portal/home/!ut/p/a1/04_Sj9CPykssy0x",
            },
            {
                "occurrence": 6,
                "type": "Employee",
                "url": "https://wiki.example.com/login.action;jsessionid=877F03D74A05",
            },
            {
                "occurrence": 2,
                "type": "Employee",
                "url": "https://hades.example.com:14001/identity/faces/signin",
            },
            {
                "occurrence": 1,
                "type": "Employee",
                "url": "https://vpn.example.com./vpn/index.html",
            },
            {"occurrence": 67, "type": "Employee", "url": "ftp://ftp.example.com"},
            {"occurrence": 5, "type": "Employee", "url": "ftp.example.com:21"},
            {"occurrence": 9, "type": "Employee", "url": "https://login.other.org/"},
        ],
        "clients_urls": [
            {"occurrence": 13103, "type": "User", "url": "https://shop.example.com"},
            {
                "occurrence": 1823,
                "type": "User",
                "url": "https://shop.example.com/?ref=abc&token=secret",
            },
            {
                "occurrence": 3312,
                "type": "User",
                "url": "https://id.example.com/ingresar/correo-contrase%C3%B1a",
            },
            {
                "occurrence": 38,
                "type": "User",
                "url": "https://id.example.com/ingresar/correo-contrase%c3%b1a",
            },
            {
                "occurrence": 223,
                "type": "User",
                "url": "https://shop.example.com//account/login",
            },
        ],
        "all_urls": [],
    },
    "stats": {},
    "antiviruses": {
        "total": 167,
        "found": 12.6,
        "list": [{"count": 69, "name": "Not Found"}],
    },
    "applications": [{"keyword": "vpn"}, {"count": 6, "keyword": "auth"}],
    "employeePasswords": {
        "totalPass": 191,
        "has_stats": True,
        "too_weak": {"qty": 21, "perc": 10.99},
        "weak": {"qty": 60, "perc": 31.41},
        "medium": {"qty": 0, "perc": 0},
        "strong": {"qty": 110, "perc": 57.59},
    },
    "userPasswords": {"totalPass": 0, "has_stats": False},
    "thirdPartyDomains": [{"occurrence": 1397, "domain": "microsoftonline.com"}],
    "stealerFamilies": {"total": 41749, "RedLine": 18191, "Lumma": 6373, "Taurus": 0},
}

COLLAPSED = {
    "total": 17,
    "employees": 0,
    "users": 17,
    "third_parties": 0,
    "totalUrls": 3,
    "data": {
        "employees_urls": [],
        "clients_urls": [
            {
                "occurrence": 30,
                "type": "User",
                "url": "https://basic.example.com/login",
            },
        ],
    },
    "is_shopify": False,
}


def _by(report, host: str, audience: str = Audience.EMPLOYEE.value):
    return [lg for lg in report.logins if lg.host == host and lg.audience == audience]


def test_a_rich_report_keeps_counts_dates_and_breakdowns():
    report = parse_domain_report(RICH, "example.com")
    assert report is not None
    assert (report.total, report.employees, report.users, report.third_parties) == (
        44368,
        308,
        42883,
        1177,
    )
    assert report.total_urls == 3561
    assert report.last_employee_at is not None
    assert report.last_employee_at.tzinfo is not None
    assert [(f.name, f.count) for f in report.families] == [
        ("RedLine", 18191),
        ("Lumma", 6373),
    ]
    assert report.passwords == {
        "employee": {"too_weak": 21, "weak": 60, "medium": 0, "strong": 110}
    }
    assert [(a.name, a.count) for a in report.applications] == [
        ("auth", 6),
        ("vpn", None),
    ]
    assert [(s.name, s.count) for s in report.services] == [
        ("microsoftonline.com", 1397)
    ]


def test_logins_are_cleaned_grouped_and_kept_under_the_domain():
    report = parse_domain_report(RICH, "example.com")
    assert report is not None
    hosts = {lg.host for lg in report.logins}
    assert "login.other.org" not in hosts
    assert [(lg.path, lg.credentials) for lg in _by(report, "vpn.example.com")] == [
        ("/vpn/index.html", 247)
    ]
    assert [(lg.path, lg.credentials) for lg in _by(report, "citrix.example.com")] == [
        ("/Citrix/XD76Web", 130)
    ]
    assert _by(report, "portal.example.com")[0].path == "/wps/portal/home"
    assert _by(report, "wiki.example.com")[0].path == "/login.action"
    assert _by(report, "hades.example.com")[0].port == 14001
    ftp = _by(report, "ftp.example.com")
    assert len(ftp) == 2
    assert {(lg.scheme, lg.port) for lg in ftp} == {("ftp", None), (None, 21)}
    shop = _by(report, "shop.example.com", Audience.USER.value)
    assert ("/", 14926) in [(lg.path, lg.credentials) for lg in shop]
    assert ("/account/login", 223) in [(lg.path, lg.credentials) for lg in shop]
    ident = _by(report, "id.example.com", Audience.USER.value)
    assert [(lg.path, lg.credentials) for lg in ident] == [
        ("/ingresar/correo-contraseña", 3350)
    ]
    assert report.logins[0].audience == Audience.EMPLOYEE.value


def test_a_collapsed_report_has_counts_and_logins_only():
    report = parse_domain_report(COLLAPSED, "example.com")
    assert report is not None
    assert report.users == 17
    assert report.last_employee_at is None
    assert report.families == []
    assert report.passwords == {}
    assert report.services == []
    assert [(lg.host, lg.path) for lg in report.logins] == [
        ("basic.example.com", "/login")
    ]


@pytest.mark.parametrize("payload", [None, [], "x", {"message": "no total"}])
def test_an_answer_without_a_total_is_unreadable(payload):
    assert parse_domain_report(payload, "example.com") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://a.example.com/x?y=1#z", ("a.example.com", None, None, "/x")),
        ("http://a.example.com:80/", ("a.example.com", None, None, "/")),
        ("https://a.example.com:8443/x/", ("a.example.com", None, 8443, "/x")),
        ("a.example.com", ("a.example.com", None, None, "/")),
        ("https://example.com", ("example.com", None, None, "/")),
        ("https://evil-example.com/", None),
        ("https://exa mple.com/", None),
        ("", None),
        (42, None),
    ],
)
def test_clean_login(raw, expected):
    assert clean_login(raw, "example.com") == expected


def test_an_over_long_path_keeps_the_host_without_the_path():
    raw = "https://a.example.com/" + "p" * 500
    assert clean_login(raw, "example.com") == ("a.example.com", None, None, None)


@pytest.mark.parametrize(
    ("value", "kind", "expected"),
    [
        ("example.com", TargetType.DOMAIN, "example.com"),
        ("shop.example.co.uk", TargetType.DOMAIN, "example.co.uk"),
        ("https://app.example.com/login", TargetType.URL, "example.com"),
        ("gov.np", TargetType.DOMAIN, None),
        ("203.0.113.9", TargetType.IP, None),
        ("AS13335", TargetType.ASN, None),
    ],
)
def test_lookup_domain(value, kind, expected):
    assert lookup_domain(value, kind) == expected


async def _seed(estate, now):
    sid = await estate.scan("example.com", "run", at=now)
    await estate.hosts(
        "run", ["vpn.example.com", "shop.example.com"], at=now, status=200
    )
    await estate.hosts("run", ["mail.example.com"], at=now, ips=["203.0.113.5"])
    await estate.hosts("run", ["old.example.com", "plain.example.com"], at=now)
    tid = estate.targets["example.com"]
    estate.session.add(
        TargetInfostealer(
            target_id=tid, domain="example.com", total=10, employees=4, users=6
        )
    )
    rows = [
        (Audience.EMPLOYEE.value, "vpn.example.com", "/vpn", 250),
        (Audience.EMPLOYEE.value, "mail.example.com", "/owa", 20),
        (Audience.USER.value, "mail.example.com", "/", 5),
        (Audience.USER.value, "shop.example.com", "/", 900),
        (Audience.EMPLOYEE.value, "old.example.com", "/", 3),
        (Audience.EMPLOYEE.value, "gone.example.com", "/", 8),
    ]
    estate.session.add_all(
        InfostealerLogin(target_id=tid, audience=a, host=h, path=p, credentials=c)
        for a, h, p, c in rows
    )
    await estate.session.flush()
    return tid, sid


async def _count(session, project_id, sid, q: str) -> int:
    result = await SubdomainService(session).search(
        project_id=project_id, scope=sid, f=SubdomainFilter(q=q, limit=50)
    )
    assert result.error is None, result.error
    return result.total


async def test_the_report_counts_equal_the_rows_its_query_opens(estate, session, now):
    tid, sid = await _seed(estate, now)
    report = await InfostealerService(session).report(tid, sid)
    assert report is not None
    standing = {h.host: h.standing for h in report.hosts}
    assert standing == {
        "vpn.example.com": HostStanding.WEB_ASSET.value,
        "shop.example.com": HostStanding.WEB_ASSET.value,
        "mail.example.com": HostStanding.RESOLVED.value,
        "old.example.com": HostStanding.UNRESOLVED.value,
        "gone.example.com": HostStanding.ABSENT.value,
    }
    assert [h.host for h in report.hosts][:2] == ["vpn.example.com", "mail.example.com"]
    pid = estate.project_id
    assert await _count(session, pid, sid, report.query) == report.in_scan == 4
    assert await _count(session, pid, sid, "infostealer:employee") == 3
    assert await _count(session, pid, sid, "infostealer:user") == 2
    assert await _count(session, pid, sid, "infostealer:none") == 1
    assert await _count(session, pid, sid, "not infostealer:any") == 1
    assert await _count(session, pid, sid, "infostealer.credentials>=25") == 3
    assert await _count(session, pid, sid, "infostealer:any is:web") == 2


async def test_a_scan_of_another_target_reads_every_host_as_absent(
    estate, session, now
):
    tid, _ = await _seed(estate, now)
    other = await estate.scan("other.org", "elsewhere", at=now)
    report = await InfostealerService(session).report(tid, other)
    assert report is not None
    assert report.scan_id is None
    assert report.in_scan == 0
    assert {h.standing for h in report.hosts} == {HostStanding.ABSENT.value}


async def test_an_unknown_value_is_a_query_error(estate, session, now):
    _, sid = await _seed(estate, now)
    result = await SubdomainService(session).search(
        project_id=estate.project_id,
        scope=sid,
        f=SubdomainFilter(q="infostealer:admin"),
    )
    assert result.error is not None
    assert "employee" in (result.error.hint or "")
