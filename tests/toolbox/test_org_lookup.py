"""Reading what was typed, matching organization names and ranking domains."""

from __future__ import annotations

from datetime import date

import pytest

from toolbox.org_lookup import (
    MAX_NAME_LENGTH,
    DomainFacts,
    InputKind,
    InputRefusedError,
    holder_name,
    lead_word,
    merge,
    org_key,
    rank,
    read,
    subject_organization,
)

ORGANIZATIONS = [
    "Uber Technologies",
    "Uber Technologies, Inc.",
    "Cloudflare, Inc.",
    "O'Reilly Media",
    "AT&T Inc.",
    "3M Company",
    "HP Inc.",
    "IBM",
    "Booking.com B.V.",
    "Société Générale",
    "Deutsche Telekom AG",
    "Sony Group Corporation",
    "株式会社ソニー",
    "The Walt Disney Company",
    "Procter & Gamble",
    "Ernst & Young LLP",
    "Samsung Electronics Co., Ltd.",
    "Alibaba (China) Co. Ltd",
    "L'Oréal S.A.",
    "Nestlé S.A.",
    "Tata Consultancy Services Limited",
    "Ørsted A/S",
    "  Uber   Technologies  ",
    "A1",
]


@pytest.mark.parametrize("raw", ORGANIZATIONS)
def test_organization_names_read_as_organizations(raw):
    query = read(raw)
    assert query.kind == InputKind.ORGANIZATION
    assert query.value == " ".join(raw.split())


DOMAINS = [
    ("uber.com", "uber.com"),
    ("UBER.COM", "uber.com"),
    ("uber.com.", "uber.com"),
    ("www.uber.com", "uber.com"),
    ("a.b.c.uber.com", "uber.com"),
    ("*.uber.com", "uber.com"),
    ("https://www.github.com/login", "github.com"),
    ("http://github.com:8443/x?y=1", "github.com"),
    ("github.com/path/to", "github.com"),
    ("bbc.co.uk", "bbc.co.uk"),
    ("news.bbc.co.uk", "bbc.co.uk"),
    ("uber.com.kz", "uber.com.kz"),
    ("mof.gov.cy", "mof.gov.cy"),
    ("police.gov.np", "police.gov.np"),
    ("example.com.br", "example.com.br"),
    ("shop.example.co.jp", "example.co.jp"),
    ("xn--mnchen-3ya.de", "xn--mnchen-3ya.de"),
    ("sub.xn--mnchen-3ya.de", "xn--mnchen-3ya.de"),
    ("autonomous.mobile", "autonomous.mobile"),
    ("x.city.kawasaki.jp", "city.kawasaki.jp"),
]


@pytest.mark.parametrize(("raw", "domain"), DOMAINS)
def test_domains_and_urls_read_as_their_registrable_domain(raw, domain):
    query = read(raw)
    assert query.kind == InputKind.DOMAIN
    assert query.value == domain


EMAILS = [
    ("hostmaster@uber.com", "hostmaster@uber.com"),
    ("DomainAdmin@Example.CO.UK", "domainadmin@example.co.uk"),
    ("john_doe@example.com", "john_doe@example.com"),
    ("a+b@sub.example.org", "a+b@sub.example.org"),
]


@pytest.mark.parametrize(("raw", "value"), EMAILS)
def test_emails_read_as_emails(raw, value):
    query = read(raw)
    assert query.kind == InputKind.EMAIL
    assert query.value == value


REFUSED = [
    ("", "Enter an organization name"),
    ("   ", "Enter an organization name"),
    ("\t\n", "Enter an organization name"),
    ("8.8.8.8", "address or network"),
    ("2606:4700::1111", "address or network"),
    ("10.0.0.0/8", "address or network"),
    ("192.168.1.1", "address or network"),
    ("AS13335", "address or network"),
    ("as13335", "address or network"),
    ("co.uk", "public suffix"),
    ("com.kz", "public suffix"),
    ("gov.cy", "public suffix"),
    ("gov.np", "public suffix"),
    ("com.br", "public suffix"),
    ("%", "cannot contain"),
    ("Uber%", "cannot contain"),
    ("Uber Tech%", "cannot contain"),
    ("Uber_Tech Inc", "cannot contain"),
    ("Domains By Proxy, LLC", "does not name an organization"),
    ("REDACTED FOR PRIVACY", "does not name an organization"),
    ("Contact Privacy Inc. Customer 1234", "does not name an organization"),
    ("Withheld for Privacy ehf", "does not name an organization"),
    ("Data Protected", "does not name an organization"),
    ("Inc.", "at least two"),
    ("LLC", "at least two"),
    ("Ltd", "at least two"),
    ("The Company", "at least two"),
    ("a", "at least two"),
    ("-", "does not name an organization"),
    ("!!!", "at least two"),
    ("Uber\x00Tech", "control characters"),
    ("Uber\x1bTech", "control characters"),
    ("x" * (MAX_NAME_LENGTH + 1), "at most"),
]


@pytest.mark.parametrize(("raw", "fragment"), REFUSED)
def test_unusable_input_is_refused_with_a_reason(raw, fragment):
    with pytest.raises(InputRefusedError) as exc:
        read(raw)
    assert fragment in str(exc.value)


SAME = [
    ("Uber Technologies", "Uber Technologies, Inc."),
    ("Uber Technologies", "UBER TECHNOLOGIES, INC."),
    ("Uber Technologies", "Uber Technologies Inc"),
    ("Uber B.V.", "Uber BV"),
    ("Uber B.V.", "Uber"),
    ("Cloudflare", "CloudFlare, Inc."),
    ("O'Reilly Media", "O'Reilly Media, Inc."),
    ("O'Reilly Media", "OReilly Media Inc."),
    ("Société Générale", "SOCIETE GENERALE"),
    ("Société Générale S.A.", "Societe Generale"),
    ("Nestlé S.A.", "Nestle"),
    ("Deutsche Telekom AG", "Deutsche Telekom"),
    ("Sony Group Corporation", "Sony Corporation"),
    ("The Walt Disney Company", "Walt Disney Co."),
    ("Samsung Electronics Co., Ltd.", "Samsung Electronics"),
    ("GitHub, Inc.", "Github Inc"),
    ("株式会社ソニー", "株式会社ソニー"),
    ("  Uber  Technologies ", "Uber Technologies"),
]


@pytest.mark.parametrize(("a", "b"), SAME)
def test_spellings_of_one_organization_share_a_key(a, b):
    assert org_key(a)
    assert org_key(a) == org_key(b)


DIFFERENT = [
    ("Uber", "Uberduck, LLC"),
    ("Uber", "UberGroup Limited"),
    ("Uber Technologies", "Uber Freight US LLC"),
    ("Uber Technologies", "Uber"),
    ("Texas A & M University", "A A R P"),
    ("Cloudflare", "CLOUDFLARENET - Cloudflare, Inc."),
    ("Meta Platforms", "Metaplex"),
    ("Apple", "Apple Hospitality REIT"),
    ("HP", "HPE"),
    ("GitHub", "GitLab"),
]


@pytest.mark.parametrize(("a", "b"), DIFFERENT)
def test_different_organizations_do_not_share_a_key(a, b):
    assert org_key(a) != org_key(b)


@pytest.mark.parametrize(
    "name",
    ["", None, "Domains By Proxy, LLC", "REDACTED FOR PRIVACY", "Inc.", "LLC", "---"],
)
def test_names_without_an_identity_have_no_key(name):
    assert org_key(name) == ""


DNS = [
    (
        "CN=*.nepalpolice.gov.np, O=NEPAL POLICE HEADQUARTER, L=Kathmandu",
        "NEPAL POLICE HEADQUARTER",
    ),
    ("CN=uber.com, O=Uber Technologies\\, Inc., L=SF, C=US", "Uber Technologies, Inc."),
    ("C=US, ST=CA, O=GitHub, Inc., CN=github.com", "GitHub, Inc."),
    ("CN=example.com", ""),
    ("", ""),
    (None, ""),
    ("CN=103.69.127.108, O=103.69.127.108, C=CN", ""),
    ("CN=x, OU=Engineering, O=Acme Corp", "Acme Corp"),
    ("cn=x, o=Acme Corp", "Acme Corp"),
    ("CN=x, O=REDACTED FOR PRIVACY", ""),
    ("CN=x, O=Inc.", ""),
    (
        "emailAddress=a@b.np, CN=Sophos, OU=OU, O=OM Networks Pvt Ltd, L=Kathmandu",
        "OM Networks Pvt Ltd",
    ),
]


@pytest.mark.parametrize(("dn", "organization"), DNS)
def test_subject_organization_reads_o_and_skips_non_organizations(dn, organization):
    assert subject_organization(dn) == organization


@pytest.mark.parametrize(
    ("description", "holder"),
    [
        ("CLOUDFLARENET - Cloudflare, Inc.", "Cloudflare, Inc."),
        ("UBER-PROD - Uber Technologies, Inc", "Uber Technologies, Inc"),
        ("IBM-RESEARCH-AS - IBM", "IBM"),
        ("CLOUDFLARENET-UK Cloudflare Inc", "CLOUDFLARENET-UK Cloudflare Inc"),
        ("", ""),
        ("A - B - C", "B - C"),
    ],
)
def test_holder_name_is_the_part_after_the_handle(description, holder):
    assert holder_name(description) == holder


@pytest.mark.parametrize(
    ("name", "word"),
    [
        ("Uber Technologies", "Uber"),
        ("Cloudflare, Inc.", "Cloudflare"),
        ("The Walt Disney Company", "Walt"),
        ("IBM", "IBM"),
        ("HP Inc.", ""),
        ("Société Générale", "Societe"),
        ("Inc. Ltd", ""),
        ("AT&T Inc.", ""),
    ],
)
def test_lead_word_is_the_first_distinctive_word(name, word):
    assert lead_word(name) == word


def test_merge_records_both_kinds_of_evidence():
    merged = merge(
        {"a.com": date(2026, 1, 1), "b.com": None},
        {"b.com": (date(2010, 5, 5), "MarkMonitor"), "c.com": (None, "")},
    )
    assert merged["a.com"].evidence == {"certificate"}
    assert merged["b.com"].evidence == {"certificate", "registration"}
    assert merged["b.com"].registrar == "MarkMonitor"
    assert merged["c.com"].last_certificate is None


def test_rank_puts_new_then_seen_then_targets_and_corroborated_first():
    facts = {
        "tracked.com": DomainFacts(evidence={"certificate", "registration"}),
        "seen.com": DomainFacts(evidence={"certificate"}),
        "both.com": DomainFacts(evidence={"certificate", "registration"}),
        "cert.com": DomainFacts(evidence={"certificate"}),
        "reg.com": DomainFacts(evidence={"registration"}),
    }
    ordered = sorted(
        facts, key=lambda n: rank(n, facts[n], {"tracked.com"}, {"seen.com"})
    )
    assert ordered == ["both.com", "cert.com", "reg.com", "seen.com", "tracked.com"]
