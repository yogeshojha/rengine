"""Well-known port → service name (naabu reports ports only, not versions)."""

from __future__ import annotations

_WELL_KNOWN: dict[int, str] = {
    21: "ftp",
    22: "ssh",
    23: "telnet",
    25: "smtp",
    53: "dns",
    80: "http",
    110: "pop3",
    111: "rpcbind",
    135: "msrpc",
    139: "netbios-ssn",
    143: "imap",
    161: "snmp",
    389: "ldap",
    443: "https",
    445: "smb",
    465: "smtps",
    587: "smtp",
    636: "ldaps",
    993: "imaps",
    995: "pop3s",
    1433: "mssql",
    1521: "oracle",
    2375: "docker",
    2376: "docker",
    3000: "http",
    3306: "mysql",
    3389: "rdp",
    5432: "postgresql",
    5601: "kibana",
    5900: "vnc",
    6379: "redis",
    7001: "weblogic",
    8000: "http",
    8008: "http",
    8080: "http",
    8443: "https",
    8888: "http",
    9000: "http",
    9200: "elasticsearch",
    9300: "elasticsearch",
    11211: "memcached",
    27017: "mongodb",
}


def service_for_port(port: int) -> str | None:
    return _WELL_KNOWN.get(port)
