from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from shared.definitions.domain_posture import CHECK_KEYS, CHECKS, SPOOFABLE_KEYS
from shared.definitions.domain_posture import PostureCheck as C
from shared.services.domain_posture import evaluate, gather
from shared.services.domain_posture.evaluate import dkim_key_bits, dmarc_tags
from shared.services.domain_posture.records import PolicyFetch, ZoneRecords, mx_host
from shared.services.domain_posture.spf import all_qualifier, lookup_count
from shared.services.domain_posture.write import zone_of

pytestmark = pytest.mark.posture


def _rsa_b64(bits: int) -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=bits)
    der = key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return base64.b64encode(der).decode()


_RSA_2048 = _rsa_b64(2048)


def _zone(**kw) -> ZoneRecords:
    rec = ZoneRecords(zone="example.com", answered=True)
    for key, value in kw.items():
        setattr(rec, key, value)
    return rec


def test_an_unanswered_zone_has_no_verdict():
    found = evaluate(ZoneRecords(zone="example.com", answered=False))
    assert found.checked == []
    assert found.issues == []


def test_a_bare_zone_fails_the_universal_checks_only():
    found = evaluate(_zone(dnssec="unsigned"))
    assert set(found.issues) == {
        C.SPF_MISSING,
        C.DMARC_MISSING,
        C.DNSSEC_MISSING,
        C.CAA_MISSING,
    }
    assert C.MTA_STS_MISSING not in found.checked, "no mail, no transport check"
    assert C.DKIM_NONE_PROBED not in found.checked


def test_spf_all_qualifiers():
    assert all_qualifier("v=spf1 include:_spf.google.com -all") == "fail"
    assert all_qualifier("v=spf1 include:_spf.google.com ~all") == "softfail"
    assert all_qualifier("v=spf1 ?all") == "neutral"
    assert all_qualifier("v=spf1 +all") == "pass"
    assert all_qualifier("v=spf1 include:x.example") == "absent"


def test_spf_any_sender_is_the_warning_and_softfail_the_note():
    open_zone = evaluate(_zone(txt=["v=spf1 +all"], dnssec="signed"))
    assert C.SPF_ANY_SENDER in open_zone.issues
    assert C.SPF_SOFT_ALL not in open_zone.issues
    soft = evaluate(_zone(txt=["v=spf1 include:a.example ~all"], dnssec="signed"))
    assert C.SPF_SOFT_ALL in soft.issues
    assert C.SPF_ANY_SENDER not in soft.issues


def test_two_spf_records_fail_together():
    found = evaluate(_zone(txt=["v=spf1 -all", "v=spf1 include:x -all"]))
    assert C.SPF_MULTIPLE in found.issues


def test_spf_lookup_count_follows_includes_and_stops_on_a_cycle():
    zone_txt = {
        "example.com": ["v=spf1 include:a.example include:b.example mx -all"],
        "a.example": ["v=spf1 a mx include:b.example -all"],
        "b.example": ["v=spf1 include:example.com ptr -all"],
    }
    count = lookup_count("example.com", zone_txt["example.com"][0], zone_txt.get)
    assert count.lookups == 8
    assert not count.capped


def test_over_ten_lookups_is_a_permanent_error():
    record = "v=spf1 " + " ".join(f"include:s{i}.example" for i in range(11)) + " -all"
    found = evaluate(_zone(txt=[record], spf_lookups=11))
    assert C.SPF_LOOKUP_LIMIT in found.issues
    assert found.evidence[C.SPF_LOOKUP_LIMIT] == "11 lookups"


def test_dmarc_policy_ladder():
    none = evaluate(_zone(dmarc=["v=DMARC1; p=none; rua=mailto:a@example.com"]))
    assert C.DMARC_NONE in none.issues
    assert C.DMARC_SUBDOMAINS_OPEN not in none.checked
    strict = evaluate(_zone(dmarc=["v=DMARC1; p=reject; sp=none; pct=50"]))
    assert C.DMARC_NONE not in strict.issues
    assert C.DMARC_SUBDOMAINS_OPEN in strict.issues
    assert C.DMARC_PARTIAL in strict.issues
    assert C.DMARC_NO_REPORTING in strict.issues
    assert strict.dmarc_policy == "reject"
    assert strict.dmarc_pct == 50


def test_dmarc_tags_take_the_first_value():
    tags = dmarc_tags("v=DMARC1; p=reject; p=none; rua=mailto:x@e.com")
    assert tags["p"] == "reject"
    assert tags["rua"] == "mailto:x@e.com"


def test_null_mx_means_no_mail_and_no_transport_checks():
    found = evaluate(_zone(mx=["."], txt=["v=spf1 -all"]))
    assert C.MTA_STS_MISSING not in found.checked
    assert C.TLS_RPT_MISSING not in found.checked
    assert C.DKIM_NONE_PROBED in found.checked, "SPF says it sends"


def test_a_receiving_zone_is_asked_for_transport_policies():
    found = evaluate(_zone(mx=["mx.example.com"]))
    assert C.MTA_STS_MISSING in found.issues
    assert C.TLS_RPT_MISSING in found.issues
    assert C.MTA_STS_NOT_ENFORCED not in found.checked


def test_mta_sts_mode_is_read_from_the_policy_file():
    enforce = evaluate(
        _zone(
            mx=["mx.example.com"],
            mta_sts=["v=STSv1; id=1"],
            policy="version: STSv1\nmode: enforce\nmx: mx.example.com\nmax_age: 86400",
            policy_fetched=True,
        )
    )
    assert C.MTA_STS_NOT_ENFORCED not in enforce.issues
    assert enforce.mta_sts_mode == "enforce"
    testing = evaluate(
        _zone(
            mx=["mx.example.com"],
            mta_sts=["v=STSv1; id=1"],
            policy="version: STSv1\nmode: testing",
            policy_fetched=True,
        )
    )
    assert C.MTA_STS_NOT_ENFORCED in testing.issues
    unread = evaluate(
        _zone(mx=["mx.example.com"], mta_sts=["v=STSv1; id=1"], policy_fetched=True)
    )
    assert unread.mta_sts_mode == "unreadable"
    assert C.MTA_STS_NOT_ENFORCED in unread.issues


def test_a_passive_run_does_not_judge_the_policy_mode():
    found = evaluate(
        _zone(mx=["mx.example.com"], mta_sts=["v=STSv1; id=1"], policy_fetched=False)
    )
    assert C.MTA_STS_NOT_ENFORCED not in found.checked


def test_dkim_absence_is_informational_and_named_as_probed():
    found = evaluate(_zone(txt=["v=spf1 -all"]))
    assert C.DKIM_NONE_PROBED in found.issues
    spec = next(c for c in CHECKS if c.key == C.DKIM_NONE_PROBED)
    assert spec.tone == "info"
    assert "probed" in spec.help


def test_dkim_key_size_is_read_from_the_record():
    assert dkim_key_bits(f"v=DKIM1; k=rsa; p={_RSA_2048}") == 2048
    assert dkim_key_bits(f"v=DKIM1; p={_rsa_b64(1024)}") == 1024
    assert dkim_key_bits("v=DKIM1; k=ed25519; p=abc") is None
    assert dkim_key_bits("v=DKIM1; p=") is None


def test_dnssec_states():
    assert C.DNSSEC_MISSING in evaluate(_zone(dnssec="unsigned")).issues
    assert C.DNSSEC_BROKEN in evaluate(_zone(dnssec="broken")).issues
    signed = evaluate(_zone(dnssec="signed"))
    assert C.DNSSEC_MISSING not in signed.issues
    assert C.DNSSEC_BROKEN not in signed.issues
    unknown = evaluate(_zone(dnssec="unknown"))
    assert C.DNSSEC_MISSING not in unknown.checked


def test_every_check_has_one_spec_and_the_spoofable_set_is_a_subset():
    assert len(CHECK_KEYS) == len(set(CHECK_KEYS)) == len(CHECKS)
    assert set(SPOOFABLE_KEYS) <= set(CHECK_KEYS)
    assert set(C) == set(CHECK_KEYS)


class _Fake:
    """A lookup that answers from a table and never for names outside it."""

    def __init__(self, table: dict[str, dict[str, list[str]]]):
        self.table = table
        self.asked: list[str] = []
        self.batches: list[list[str]] = []

    def records(self, names, _types):
        self.asked.extend(names)
        self.batches.append(list(names))
        return {n: self.table[n] for n in names if n in self.table}

    def dnssec(self, _zone):
        return "signed"

    def policy(self, _zone):
        return PolicyFetch(reached=True, body="version: STSv1\nmode: enforce")


def test_gather_reads_each_label_and_skips_dead_zones():
    lookup = _Fake(
        {
            "example.com": {
                "txt": ["v=spf1 include:_spf.example.net -all"],
                "mx": ["10 mx1.example.com."],
                "caa": ["letsencrypt.org"],
                "soa": ["ns1.example.com"],
            },
            "_dmarc.example.com": {"txt": ["v=DMARC1; p=reject"]},
            "_mta-sts.example.com": {"txt": ["v=STSv1; id=20240101"]},
            "google._domainkey.example.com": {
                "txt": [f"v=DKIM1; k=rsa; p={_RSA_2048}"]
            },
            "_spf.example.net": {"txt": ["v=spf1 ip4:10.0.0.0/8 -all"]},
        }
    )
    found = gather(
        ["example.com", "dead.example"],
        lookup,
        selectors=["google", "default"],
        fetch_policy=True,
    )
    live, dead = found["example.com"], found["dead.example"]
    assert dead.answered is False
    assert live.answered is True
    assert live.mx == ["mx1.example.com"]
    assert live.dmarc == ["v=DMARC1; p=reject"]
    assert live.mta_sts
    assert live.policy_fetched
    assert live.dkim == {"google": f"v=DKIM1; k=rsa; p={_RSA_2048}"}
    assert live.spf_lookups == 1
    assert "_dmarc.dead.example" not in lookup.asked

    posture = evaluate(live)
    assert set(posture.issues) == {C.DMARC_NO_REPORTING, C.TLS_RPT_MISSING}
    assert posture.dkim_key_bits == 2048


def test_mx_values_drop_the_preference_and_keep_the_null_marker():
    assert mx_host("10 aspmx.l.google.com.") == "aspmx.l.google.com"
    assert mx_host("smtp.google.com") == "smtp.google.com"
    assert mx_host("0 .") == "."
    assert mx_host(".") == "."
    assert ZoneRecords(zone="z", mx=[mx_host("0 .")]).null_mx is True


def test_dual_cidr_mechanisms_count_as_lookups():
    count = lookup_count(
        "e.com", "v=spf1 a/24 mx//64 include:a.example -all", lambda _n: None
    )
    assert count.lookups == 3


def test_a_redirect_delegates_the_all_qualifier():
    table = {"_spf.example.net": ["v=spf1 ip4:10.0.0.0/8 -all"]}
    lookup = _Fake(
        {k: {"txt": v} for k, v in table.items()}
        | {"example.com": {"txt": ["v=spf1 redirect=_spf.example.net"], "soa": ["x"]}}
    )
    found = gather(["example.com"], lookup, selectors=[], fetch_policy=False)
    rec = found["example.com"]
    assert rec.spf_redirect_all == "fail"
    posture = evaluate(rec)
    assert C.SPF_SOFT_ALL not in posture.issues
    assert posture.spf_all == "fail"


def test_an_unreached_policy_host_leaves_the_mode_unjudged():
    class _Down(_Fake):
        def policy(self, _zone):
            return PolicyFetch(reached=False)

    lookup = _Down(
        {
            "example.com": {"mx": ["10 mx.example.com"], "soa": ["x"]},
            "_mta-sts.example.com": {"txt": ["v=STSv1; id=1"]},
        }
    )
    rec = gather(["example.com"], lookup, selectors=[], fetch_policy=True)[
        "example.com"
    ]
    assert rec.policy_fetched is False
    assert C.MTA_STS_NOT_ENFORCED not in evaluate(rec).checked


def test_the_longest_zone_wins_and_lookalikes_do_not_match():
    zones = ["gov.np", "moe.gov.np", "a_c.com"]
    assert zone_of("www.moe.gov.np", zones) == "moe.gov.np"
    assert zone_of("www.gov.np", zones) == "gov.np"
    assert zone_of("x.abc.com", zones) is None
    assert zone_of("mail.a_c.com", zones) == "a_c.com"
    assert zone_of("evilgov.np", zones) is None


def test_a_capped_lookup_count_is_not_a_pass():
    under = evaluate(
        _zone(txt=["v=spf1 include:a -all"], spf_lookups=4, spf_lookups_capped=True)
    )
    assert C.SPF_LOOKUP_LIMIT not in under.checked
    over = evaluate(
        _zone(txt=["v=spf1 include:a -all"], spf_lookups=12, spf_lookups_capped=True)
    )
    assert C.SPF_LOOKUP_LIMIT in over.issues
    assert over.evidence[C.SPF_LOOKUP_LIMIT] == "12+ lookups"


def test_include_chains_are_resolved_in_batches_not_per_name():
    table = {
        "example.com": {
            "txt": ["v=spf1 include:a.example include:b.example -all"],
            "soa": ["x"],
        },
        "a.example": {"txt": ["v=spf1 include:c.example -all"]},
        "b.example": {"txt": ["v=spf1 mx -all"]},
        "c.example": {"txt": ["v=spf1 ip4:1.2.3.4 -all"]},
    }
    lookup = _Fake(table)
    rec = gather(["example.com"], lookup, selectors=[], fetch_policy=False)[
        "example.com"
    ]
    assert rec.spf_lookups == 4
    assert not rec.spf_lookups_capped
    batches = [
        n for n in lookup.batches if n and not n[0].startswith(("example.com", "_"))
    ]
    assert batches == [["a.example", "b.example"], ["c.example"]]


def test_a_mail_host_inherits_the_parent_dmarc_through_sp():
    lookup = _Fake(
        {
            "example.com": {"txt": ["v=spf1 -all"], "soa": ["x"]},
            "_dmarc.example.com": {
                "txt": ["v=DMARC1; p=reject; sp=none; rua=mailto:a@e.com"]
            },
            "mail.example.com": {"mx": ["10 mx.example.com"], "soa": ["x"]},
        }
    )
    found = gather(
        {"example.com": None, "mail.example.com": "example.com"},
        lookup,
        selectors=[],
        fetch_policy=False,
    )
    mail = found["mail.example.com"]
    assert mail.parent == "example.com"
    assert mail.dmarc_inherited is True
    posture = evaluate(mail)
    assert posture.dmarc_policy == "none"
    assert C.DMARC_NONE in posture.issues
    assert C.DMARC_SUBDOMAINS_OPEN not in posture.checked
    assert "inherited from example.com" in posture.evidence[C.DMARC_NONE]
    parent = evaluate(found["example.com"])
    assert C.DMARC_SUBDOMAINS_OPEN in parent.issues


def test_a_mail_host_with_its_own_record_is_judged_on_it():
    lookup = _Fake(
        {
            "example.com": {"soa": ["x"]},
            "_dmarc.example.com": {"txt": ["v=DMARC1; p=none"]},
            "mail.example.com": {"mx": ["10 mx.example.com"], "soa": ["x"]},
            "_dmarc.mail.example.com": {
                "txt": ["v=DMARC1; p=reject; rua=mailto:a@e.com"]
            },
        }
    )
    found = gather(
        {"example.com": None, "mail.example.com": "example.com"},
        lookup,
        selectors=[],
        fetch_policy=False,
    )
    mail = evaluate(found["mail.example.com"])
    assert found["mail.example.com"].dmarc_inherited is False
    assert mail.dmarc_policy == "reject"
    assert C.DMARC_NONE not in mail.issues


def test_a_mail_row_skips_the_zone_checks_and_a_stray_txt_does_not_block_inheritance():
    lookup = _Fake(
        {
            "example.com": {"soa": ["x"], "caa": ["letsencrypt.org"]},
            "_dmarc.example.com": {"txt": ["v=DMARC1; p=reject; rua=mailto:a@e.com"]},
            "mail.example.com": {"mx": ["10 mx.example.com"], "soa": ["x"]},
            "_dmarc.mail.example.com": {"txt": ["MS=ms12345"]},
        }
    )
    found = gather(
        {"example.com": None, "mail.example.com": "example.com"},
        lookup,
        selectors=[],
        fetch_policy=False,
    )
    mail = found["mail.example.com"]
    assert mail.dmarc_inherited is True
    posture = evaluate(mail)
    assert C.DMARC_MISSING not in posture.issues
    assert C.CAA_MISSING not in posture.checked
    assert C.DNSSEC_MISSING not in posture.checked


def test_a_mail_row_whose_parent_never_answered_leaves_dmarc_unjudged():
    lookup = _Fake({"mail.example.com": {"mx": ["10 mx.example.com"], "soa": ["x"]}})
    found = gather(
        {"example.com": None, "mail.example.com": "example.com"},
        lookup,
        selectors=[],
        fetch_policy=False,
    )
    posture = evaluate(found["mail.example.com"])
    assert found["mail.example.com"].dmarc_unknown is True
    assert C.DMARC_MISSING not in posture.checked
