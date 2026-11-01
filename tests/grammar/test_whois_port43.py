"""Port-43 WHOIS parsing, for a registry with no RDAP server."""

from datetime import UTC, datetime

import pytest

from tools.whois.parser import parse_domain_response
from tools.whois.providers.port43 import to_whoisit_shape

pytestmark = pytest.mark.grammar

BE_RESPONSE = """\
% .be Whois Server 6.1
%

Domain:\tvlaanderen.be
Status:\tNOT AVAILABLE
Registered:\tWed Mar 20 1996

Registrant:
\tNot shown, please visit www.dnsbelgium.be for webbased whois.

Registrar Technical Contacts:

Registrar:
\tName:\tCombell nv
\tWebsite:\thttps://www.combell.com

Nameservers:
\tns2.f5clouddns.com
\tns1.f5clouddns.com

Keys:
\tkeyTag:6993 flags:KSK protocol:3 algorithm:ECDSAP256SHA256 pubKey:abc==

Flags:
\tclientTransferProhibited

Please visit www.dnsbelgium.be for more info.
"""

GTLD_RESPONSE = """\
Domain Name: EXAMPLE.ORG
Registry Domain ID: D123-LROR
Updated Date: 2024-01-02T03:04:05Z
Creation Date: 1995-08-31T04:00:00Z
Registry Expiry Date: 2026-08-30T04:00:00Z
Registrar: Example Registrar, Inc.
Registrar Abuse Contact Email: abuse@example.net
Domain Status: clientTransferProhibited https://icann.org/epp#clientTransferProhibited
Registrant Organization: Example Org
Name Server: A.IANA-SERVERS.NET
Name Server: B.IANA-SERVERS.NET
DNSSEC: signedDelegation
>>> Last update of WHOIS database: 2024-01-02T03:04:05Z <<<
"""


def test_be_sectioned_layout():
    raw = to_whoisit_shape("vlaanderen.be", "whois.dns.be", BE_RESPONSE)
    response = parse_domain_response(raw, "vlaanderen.be")
    fields = response.to_db_fields()

    assert fields["registrar_name"] == "Combell nv"
    assert fields["registrant_name"] == ""
    assert fields["registration_date"] == datetime(1996, 3, 20, tzinfo=UTC)
    assert fields["nameservers"] == ["ns2.f5clouddns.com", "ns1.f5clouddns.com"]
    assert fields["domain_status"] == ["clientTransferProhibited"]
    assert fields["dnssec"] is True
    assert fields["whois_server"] == "whois.dns.be"


def test_gtld_flat_layout():
    raw = to_whoisit_shape("example.org", "whois.pir.org", GTLD_RESPONSE)
    response = parse_domain_response(raw, "example.org")
    fields = response.to_db_fields()

    assert fields["registrar_name"] == "Example Registrar, Inc."
    assert fields["registrant_name"] == "Example Org"
    assert fields["abuse_email"] == "abuse@example.net"
    assert fields["registration_date"] == datetime(1995, 8, 31, 4, tzinfo=UTC)
    assert fields["expiration_date"] == datetime(2026, 8, 30, 4, tzinfo=UTC)
    assert fields["nameservers"] == ["a.iana-servers.net", "b.iana-servers.net"]
    assert fields["domain_status"] == ["clientTransferProhibited"]
    assert fields["dnssec"] is True
