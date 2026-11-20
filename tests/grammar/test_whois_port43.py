"""Port-43 WHOIS parsing, for a registry with no RDAP server."""

import time
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


def _fields(domain: str, server: str, text: str) -> dict:
    raw = to_whoisit_shape(domain, server, text)
    return parse_domain_response(raw, domain).to_db_fields()


IT_RESPONSE = """\
*********************************************************************
* Please note that the following result could be a subgroup of      *
* the data contained in the database.                               *
*********************************************************************

Domain:             example.it
Status:             ok
Signed:             no
Created:            1999-12-10 00:00:00
Last Update:        2026-06-09 23:13:34
Expire Date:        2027-04-21

Registrant
  Organization:     Example Holdings Limited
  Address:          1 Example Quay
                    Dublin
                    IE
  Created:          2018-03-02 19:04:02

Registrar
  Organization:     Example Registrar Limited
  Name:             EXAMPLE-REG
  Web:              https://registrar.example

Nameservers
  ns1.example.net
  ns2.example.net
"""

JP_RESPONSE = """\
[ JPRS database provides information on network administration. Its use is    ]
[ restricted to network administration purposes.                              ]
Domain Information:
[Domain Name]                   EXAMPLE.JP

[Registrant]                    Example LLC

[Name Server]                   ns1.example.net
[Name Server]                   ns2.example.net
[Signing Key]

[Created on]                    2005/05/30
[Expires on]                    2027/05/31
[Status]                        Active
[Last Updated]                  2026/06/01 01:05:03 (JST)
"""

KZ_RESPONSE = """\
Whois Server for the .kz top level domain.

Domain Name............: example.kz

Registrant
Name...................: Example Inc.
Organization Name......: Example Inc.
City...................: Almaty

Name Server list
Name Server............: ns1.example.net
IP Address.............: 192.0.2.10
Name Server............: ns2.example.net

Domain created.........: 1999-06-07 14:01:43 (GMT+0:00)
Last modified..........: 2012-11-28 04:16:59 (GMT+0:00)
Expiration date........: 2027-06-06 19:00:00 (GMT+0:00)
Domain status..........: ok - Normal state.
"""

EE_RESPONSE = """\
Estonia .ee Top Level Domain WHOIS server

Domain:
name:       example.ee
status:     ok (paid and in zone)
registered: 2010-07-04 04:34:46 +03:00
changed:    2026-10-19 19:45:09 +03:00
expire:     2027-11-09

Registrant:
name:       Example LLC
country:    US
changed:    2020-01-01 10:00:00 +03:00

Registrar:
name:       Example Registrar OU
url:        http://registrar.example
changed:    2019-07-24 10:58:40 +03:00

Name servers:
nserver:   ns1.example.net
nserver:   ns2.example.net
"""

AT_RESPONSE = """\
domain:            example.at
registrar:         Example Registrar Inc. ( https://nic.at/registrar/1 )
registrant:        EX123-NICAT
nserver:           ns1.example.net
nserver:           ns2.example.net
changed:           20241113 19:36:02
registered:        20001204 20:03:13
source:            AT-DOM

personname:        Domain Administrator
organization:      Example LLC
nic-hdl:           EX123-NICAT
changed:           20180302 18:52:05
source:            AT-DOM
"""

TR_RESPONSE = """\
** Domain Name: example.tr
Domain Status: Active

** Registrant:
Example LLC
Hidden upon user request

** Registrar:
NIC Handle\t\t: ex40
Organization Name\t: Example Registrar A.S.

** Domain Servers:
ns1.example.net
ns2.example.net

** Additional Info:
Created on..............: 2024-Aug-26.
Expires on..............: 2027-Aug-25.
"""

RU_RESPONSE = """\
domain:        EXAMPLE.RU
nserver:       ns1.example.net.
nserver:       ns2.example.net.
state:         REGISTERED, DELEGATED, VERIFIED
org:
registrar:     EXAMPLE-RU
created:       2004-03-03T21:00:00Z
paid-till:     2027-03-04T21:00:00Z
source:        TCI
"""

EU_RESPONSE = """\
Domain: example.eu
Script: LATIN

Registrant:
        NOT DISCLOSED!
        Visit www.eurid.eu for the web-based WHOIS.

Registrar:
        Name: Example Registrar Inc.
        Website: https://registrar.example/

Name servers:
        ns1.example.net (192.0.2.1)
        ns2.example.net
"""


def test_a_header_without_a_colon_opens_a_section():
    fields = _fields("example.it", "whois.nic.it", IT_RESPONSE)

    assert fields["registrar_name"] == "Example Registrar Limited"
    assert fields["registrant_name"] == "Example Holdings Limited"
    assert fields["registration_date"] == datetime(1999, 12, 10, tzinfo=UTC)
    assert fields["last_changed_date"] == datetime(2026, 6, 9, 23, 13, 34, tzinfo=UTC)
    assert fields["expiration_date"] == datetime(2027, 4, 21, tzinfo=UTC)
    assert fields["nameservers"] == ["ns1.example.net", "ns2.example.net"]
    assert fields["domain_status"] == ["ok"]
    assert fields["dnssec"] is False


def test_bracketed_keys_and_a_named_zone():
    fields = _fields("example.jp", "whois.jprs.jp", JP_RESPONSE)

    assert fields["registrant_name"] == "Example LLC"
    assert fields["nameservers"] == ["ns1.example.net", "ns2.example.net"]
    assert fields["registration_date"] == datetime(2005, 5, 30, tzinfo=UTC)
    assert fields["expiration_date"] == datetime(2027, 5, 31, tzinfo=UTC)
    assert fields["last_changed_date"] == datetime(2026, 5, 31, 16, 5, 3, tzinfo=UTC)
    assert fields["domain_status"] == ["Active"]


def test_dot_leaders_and_an_offset_note():
    fields = _fields("example.kz", "whois.nic.kz", KZ_RESPONSE)

    assert fields["registrant_name"] == "Example Inc."
    assert fields["nameservers"] == ["ns1.example.net", "ns2.example.net"]
    assert fields["registration_date"] == datetime(1999, 6, 7, 14, 1, 43, tzinfo=UTC)
    assert fields["expiration_date"] == datetime(2027, 6, 6, 19, tzinfo=UTC)
    assert fields["domain_status"] == ["ok"]


def test_a_section_holds_lines_that_are_not_indented():
    fields = _fields("example.ee", "whois.tld.ee", EE_RESPONSE)

    assert fields["registrar_name"] == "Example Registrar OU"
    assert fields["registrant_name"] == "Example LLC"
    assert fields["registration_date"] == datetime(2010, 7, 4, 1, 34, 46, tzinfo=UTC)
    assert fields["last_changed_date"] == datetime(2026, 10, 19, 16, 45, 9, tzinfo=UTC)
    assert fields["expiration_date"] == datetime(2027, 11, 9, tzinfo=UTC)
    assert fields["nameservers"] == ["ns1.example.net", "ns2.example.net"]
    assert fields["domain_status"] == ["ok"]


def test_a_registrant_handle_is_read_from_its_own_block():
    fields = _fields("example.at", "whois.nic.at", AT_RESPONSE)

    assert fields["registrant_name"] == "Example LLC"
    assert fields["registrar_name"] == "Example Registrar Inc."
    assert fields["registration_date"] == datetime(2000, 12, 4, 20, 3, 13, tzinfo=UTC)
    assert fields["last_changed_date"] == datetime(2024, 11, 13, 19, 36, 2, tzinfo=UTC)


def test_starred_headers_and_bare_value_lines():
    fields = _fields("example.tr", "whois.trabis.gov.tr", TR_RESPONSE)

    assert fields["registrant_name"] == "Example LLC"
    assert fields["registrar_name"] == "Example Registrar A.S."
    assert fields["nameservers"] == ["ns1.example.net", "ns2.example.net"]
    assert fields["registration_date"] == datetime(2024, 8, 26, tzinfo=UTC)
    assert fields["expiration_date"] == datetime(2027, 8, 25, tzinfo=UTC)


def test_comma_separated_states_are_split():
    fields = _fields("example.ru", "whois.tcinet.ru", RU_RESPONSE)

    assert fields["domain_status"] == ["REGISTERED", "DELEGATED", "VERIFIED"]
    assert fields["registrar_name"] == "EXAMPLE-RU"
    assert fields["nameservers"] == ["ns1.example.net", "ns2.example.net"]
    assert fields["expiration_date"] == datetime(2027, 3, 4, 21, tzinfo=UTC)


def test_a_withheld_registrant_is_empty():
    fields = _fields("example.eu", "whois.eu", EU_RESPONSE)

    assert fields["registrant_name"] == ""
    assert fields["registrar_name"] == "Example Registrar Inc."
    assert fields["nameservers"] == ["ns1.example.net", "ns2.example.net"]


GLUE_RESPONSE = """\
Domain:\texample.be
Status:\tNOT AVAILABLE

Nameservers:
\tns1.example.be 2001:db8::53
\tns2.example.be (2001:db8::54)
\tns3.example.net
"""

CONTACT_RESPONSE = """\
domain:       example.cz
registrant:   EXAMPLE-ID
nserver:      ns1.example.net
registered:   15.05.1998 02:00:00
expire:       15.05.2027

contact:      EXAMPLE-ID
org:          Example s.r.o.
created:      02.03.2001 00:00:00
"""


def test_a_glue_address_does_not_hide_its_nameserver():
    fields = _fields("example.be", "whois.dns.be", GLUE_RESPONSE)

    assert fields["nameservers"] == [
        "ns1.example.be",
        "ns2.example.be",
        "ns3.example.net",
    ]


def test_a_contact_block_date_is_not_the_domain_date():
    fields = _fields("example.cz", "whois.nic.cz", CONTACT_RESPONSE)

    assert fields["registration_date"] == datetime(1998, 5, 15, 2, tzinfo=UTC)
    assert fields["expiration_date"] == datetime(2027, 5, 15, tzinfo=UTC)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2024-01-02 10:00:00 JST", datetime(2024, 1, 2, 1, tzinfo=UTC)),
        ("2024/01/02 10:00:00 (JST)", datetime(2024, 1, 2, 1, tzinfo=UTC)),
        ("2024-01-02 10:00:00 CLST", datetime(2024, 1, 2, 13, tzinfo=UTC)),
        ("2024-01-02 10:00:00 UTC", datetime(2024, 1, 2, 10, tzinfo=UTC)),
        ("2024-01-02 10:00:00 (GMT+3:00)", datetime(2024, 1, 2, 7, tzinfo=UTC)),
        ("2024-01-02 10:00:00 XYZT", None),
    ],
)
def test_a_zone_moves_the_instant_and_an_unknown_one_is_no_date(value, expected):
    text = f"Domain Name: example.org\nCreation Date: {value}\n"
    raw = to_whoisit_shape("example.org", "whois.example", text)

    assert raw["registration_date"] == expected


def test_a_crlf_reply_reads_like_an_lf_one():
    crlf = to_whoisit_shape(
        "example.org", "whois.pir.org", GTLD_RESPONSE.replace("\n", "\r\n")
    )
    lf = to_whoisit_shape("example.org", "whois.pir.org", GTLD_RESPONSE)

    assert crlf == lf


@pytest.mark.parametrize(
    "line", ["[" + "\t" * 60_000 + "x", "." * 120_000, "(" * 60_000, " " * 120_000]
)
def test_a_hostile_line_is_read_in_linear_time(line: str):
    started = time.monotonic()
    to_whoisit_shape("example.org", "whois.example", f"Registrar: {line}\n{line}\n")

    assert time.monotonic() - started < 1


def test_a_domain_qualified_date_wins_over_a_contact_date():
    text = (
        KZ_RESPONSE + "\nAdministrative Contact\nCreated................: 2012-05-05\n"
    )
    fields = _fields("example.kz", "whois.nic.kz", text)

    assert fields["registration_date"] == datetime(1999, 6, 7, 14, 1, 43, tzinfo=UTC)
