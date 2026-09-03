"""Ports, services and exposure classes — the SSOT for the scan pipeline and the query layer."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

MAX_PORT = 65535
DEFAULT_WEB_PORTS: tuple[int, ...] = (80, 443)


class ServiceClass(StrEnum):
    WEB = "web"
    REMOTE = "remote"
    DATABASE = "database"
    MAIL = "mail"
    INFRA = "infra"
    OTHER = "other"


SERVICE_CLASS_LABELS: dict[str, str] = {
    ServiceClass.WEB.value: "Web",
    ServiceClass.REMOTE.value: "Remote access",
    ServiceClass.DATABASE.value: "Data store",
    ServiceClass.MAIL.value: "Mail",
    ServiceClass.INFRA.value: "Infrastructure",
    ServiceClass.OTHER.value: "Other",
}

# a service belongs to exactly one class; order is the tab order, not a precedence
SERVICE_CLASS_ORDER: tuple[str, ...] = tuple(SERVICE_CLASS_LABELS)


class PortState(StrEnum):
    OPEN = "open"
    FILTERED = "filtered"
    CLOSED = "closed"


class PortSource(StrEnum):
    NAABU = "naabu"
    INTERNETDB = "internetdb"
    HTTP_PROBE = "http_probe"
    BANNER = "banner"


PORT_SOURCE_LABELS: dict[str, str] = {
    PortSource.NAABU.value: "Port scan",
    PortSource.INTERNETDB.value: "External scanner",
    PortSource.HTTP_PROBE.value: "HTTP probe",
    PortSource.BANNER.value: "Service banner",
}

# active observation outranks passive intel when both report the same port
PORT_SOURCE_RANK: dict[str, int] = {
    PortSource.INTERNETDB.value: 0,
    PortSource.BANNER.value: 1,
    PortSource.HTTP_PROBE.value: 2,
    PortSource.NAABU.value: 3,
}


class ScanPolicy(StrEnum):
    FULL = "full"
    WEB = "web"
    SKIP = "skip"


SCAN_POLICY_LABELS: dict[str, str] = {
    ScanPolicy.FULL.value: "Scanned in full",
    ScanPolicy.WEB.value: "Web ports only",
    ScanPolicy.SKIP.value: "Not scanned",
}


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    label: str
    klass: str
    description: str = ""
    tls: bool = False


def _s(
    name: str,
    label: str,
    klass: ServiceClass,
    description: str = "",
    *,
    tls: bool = False,
) -> ServiceSpec:
    return ServiceSpec(
        name=name,
        label=label,
        klass=klass.value,
        description=description,
        tls=tls,
    )


# port -> canonical service. Keep names lowercase and stable: they are query values.
WELL_KNOWN: dict[int, ServiceSpec] = {
    21: _s(
        "ftp",
        "FTP",
        ServiceClass.INFRA,
        "File transfer, credentials in the clear unless FTPS",
    ),
    22: _s("ssh", "SSH", ServiceClass.REMOTE, "Secure Shell remote administration"),
    23: _s("telnet", "Telnet", ServiceClass.REMOTE, "Telnet remote shell, unencrypted"),
    25: _s("smtp", "SMTP", ServiceClass.MAIL, "Mail transfer between servers"),
    53: _s("dns", "DNS", ServiceClass.INFRA, "Domain name resolution"),
    69: _s(
        "tftp", "TFTP", ServiceClass.INFRA, "Trivial file transfer, no authentication"
    ),
    88: _s("kerberos", "Kerberos", ServiceClass.INFRA, "Kerberos authentication"),
    110: _s("pop3", "POP3", ServiceClass.MAIL, "Mailbox retrieval, unencrypted"),
    111: _s(
        "rpcbind",
        "RPC portmapper",
        ServiceClass.INFRA,
        "RPC portmapper, enumerates other services",
    ),
    135: _s("msrpc", "MSRPC", ServiceClass.INFRA, "Windows RPC endpoint mapper"),
    137: _s("netbios", "NetBIOS", ServiceClass.INFRA, "NetBIOS name service"),
    139: _s(
        "netbios-ssn",
        "NetBIOS session",
        ServiceClass.INFRA,
        "NetBIOS session service over SMB",
    ),
    143: _s("imap", "IMAP", ServiceClass.MAIL, "Mailbox access, unencrypted"),
    161: _s(
        "snmp",
        "SNMP",
        ServiceClass.INFRA,
        "SNMP management, often left on a default community string",
    ),
    389: _s("ldap", "LDAP", ServiceClass.INFRA, "Directory service, unencrypted"),
    427: _s("slp", "SLP", ServiceClass.INFRA, "Service Location Protocol"),
    443: _s("https", "HTTPS", ServiceClass.WEB, "Web server over TLS", tls=True),
    445: _s("smb", "SMB", ServiceClass.INFRA, "Windows file sharing"),
    465: _s(
        "smtps",
        "SMTPS",
        ServiceClass.MAIL,
        "Mail submission over implicit TLS",
        tls=True,
    ),
    500: _s("isakmp", "IKE", ServiceClass.INFRA, "IPsec key exchange"),
    512: _s(
        "rexec", "rexec", ServiceClass.REMOTE, "Remote command execution, unencrypted"
    ),
    513: _s("rlogin", "rlogin", ServiceClass.REMOTE, "Remote login, unencrypted"),
    514: _s("syslog", "Syslog", ServiceClass.INFRA, "Syslog collection"),
    515: _s("printer", "LPD", ServiceClass.INFRA, "Line printer daemon"),
    548: _s("afp", "AFP", ServiceClass.INFRA, "Apple file sharing"),
    554: _s("rtsp", "RTSP", ServiceClass.OTHER, "Streaming media control"),
    587: _s(
        "smtp", "SMTP submission", ServiceClass.MAIL, "Authenticated mail submission"
    ),
    623: _s(
        "ipmi",
        "IPMI",
        ServiceClass.INFRA,
        "Baseboard management controller, out-of-band server access",
    ),
    636: _s(
        "ldaps", "LDAPS", ServiceClass.INFRA, "Directory service over TLS", tls=True
    ),
    873: _s("rsync", "rsync", ServiceClass.INFRA, "rsync file synchronisation"),
    993: _s("imaps", "IMAPS", ServiceClass.MAIL, "Mailbox access over TLS", tls=True),
    995: _s(
        "pop3s", "POP3S", ServiceClass.MAIL, "Mailbox retrieval over TLS", tls=True
    ),
    1080: _s(
        "socks",
        "SOCKS proxy",
        ServiceClass.INFRA,
        "SOCKS proxy. An open proxy relays traffic for any client.",
    ),
    1433: _s(
        "mssql", "Microsoft SQL Server", ServiceClass.DATABASE, "Microsoft SQL Server"
    ),
    1521: _s("oracle", "Oracle DB", ServiceClass.DATABASE, "Oracle database listener"),
    1723: _s("pptp", "PPTP", ServiceClass.REMOTE, "PPTP VPN, cryptographically broken"),
    2049: _s("nfs", "NFS", ServiceClass.INFRA, "Network file system export"),
    2181: _s(
        "zookeeper",
        "ZooKeeper",
        ServiceClass.INFRA,
        "ZooKeeper coordination, usually unauthenticated",
    ),
    2375: _s(
        "docker",
        "Docker API",
        ServiceClass.INFRA,
        "Docker API without TLS, equivalent to root on the host",
    ),
    2376: _s(
        "docker", "Docker API", ServiceClass.INFRA, "Docker API over TLS", tls=True
    ),
    2379: _s(
        "etcd",
        "etcd",
        ServiceClass.DATABASE,
        "etcd key-value store, holds cluster secrets",
    ),
    3128: _s("http-proxy", "HTTP proxy", ServiceClass.WEB, "Forward web proxy"),
    3268: _s(
        "ldap", "Global catalog", ServiceClass.INFRA, "Active Directory global catalog"
    ),
    3306: _s("mysql", "MySQL", ServiceClass.DATABASE, "MySQL or MariaDB database"),
    3389: _s("rdp", "RDP", ServiceClass.REMOTE, "Windows remote desktop"),
    4369: _s(
        "epmd",
        "Erlang port mapper",
        ServiceClass.INFRA,
        "Erlang port mapper, enumerates node names",
    ),
    4444: _s(
        "metasploit",
        "Metasploit",
        ServiceClass.OTHER,
        "Common Metasploit listener port",
    ),
    5060: _s("sip", "SIP", ServiceClass.OTHER, "SIP telephony signalling"),
    5222: _s("xmpp", "XMPP", ServiceClass.OTHER, "XMPP client connection"),
    5353: _s("mdns", "mDNS", ServiceClass.INFRA, "Multicast DNS"),
    5432: _s("postgresql", "PostgreSQL", ServiceClass.DATABASE, "PostgreSQL database"),
    5601: _s(
        "kibana", "Kibana", ServiceClass.WEB, "Kibana dashboards for Elasticsearch"
    ),
    5672: _s("amqp", "AMQP", ServiceClass.INFRA, "AMQP message broker"),
    5900: _s(
        "vnc", "VNC", ServiceClass.REMOTE, "VNC remote desktop, often password-only"
    ),
    5901: _s("vnc", "VNC", ServiceClass.REMOTE, "VNC remote desktop, second display"),
    5984: _s(
        "couchdb",
        "CouchDB",
        ServiceClass.DATABASE,
        "CouchDB, unauthenticated in older releases",
    ),
    6379: _s(
        "redis", "Redis", ServiceClass.DATABASE, "Redis, no authentication by default"
    ),
    7001: _s(
        "weblogic",
        "WebLogic",
        ServiceClass.WEB,
        "Oracle WebLogic admin and application traffic",
    ),
    7199: _s(
        "cassandra",
        "Cassandra JMX",
        ServiceClass.DATABASE,
        "Cassandra JMX, remote code execution if exposed",
    ),
    8086: _s(
        "influxdb", "InfluxDB", ServiceClass.DATABASE, "InfluxDB time-series database"
    ),
    8500: _s(
        "consul",
        "Consul",
        ServiceClass.WEB,
        "Consul service catalogue and key-value store",
    ),
    8834: _s(
        "nessus", "Nessus", ServiceClass.WEB, "Nessus vulnerability scanner console"
    ),
    9042: _s(
        "cassandra", "Cassandra", ServiceClass.DATABASE, "Cassandra native protocol"
    ),
    9092: _s("kafka", "Kafka", ServiceClass.INFRA, "Kafka broker"),
    9160: _s(
        "cassandra",
        "Cassandra Thrift",
        ServiceClass.DATABASE,
        "Cassandra Thrift interface",
    ),
    9200: _s(
        "elasticsearch",
        "Elasticsearch",
        ServiceClass.DATABASE,
        "Elasticsearch REST API, unauthenticated in older releases",
    ),
    9300: _s(
        "elasticsearch",
        "Elasticsearch transport",
        ServiceClass.DATABASE,
        "Elasticsearch node transport",
    ),
    10250: _s("kubelet", "kubelet", ServiceClass.WEB, "Kubernetes node agent API"),
    11211: _s(
        "memcached",
        "Memcached",
        ServiceClass.DATABASE,
        "Memcached, no authentication and usable for amplification",
    ),
    15672: _s(
        "rabbitmq", "RabbitMQ", ServiceClass.WEB, "RabbitMQ management interface"
    ),
    27017: _s(
        "mongodb",
        "MongoDB",
        ServiceClass.DATABASE,
        "MongoDB, unauthenticated before the 3.6 defaults",
    ),
    27018: _s(
        "mongodb", "MongoDB shard", ServiceClass.DATABASE, "MongoDB shard member"
    ),
    50000: _s("db2", "IBM Db2", ServiceClass.DATABASE, "IBM Db2 database"),
}

# ports that commonly answer HTTP; the web probe seeds every host with these
WEB_PORTS: tuple[int, ...] = (
    80, 81, 88, 443, 591, 593, 832, 981, 1010, 1099, 1311, 2082, 2083, 2086, 2087,
    2095, 2096, 2480, 3000, 3001, 3002, 3003, 3128, 3333, 4243, 4443, 4567, 4711,
    4712, 4993, 5000, 5001, 5104, 5108, 5280, 5281, 5601, 5800, 6543, 7000, 7001,
    7002, 7396, 7474, 8000, 8001, 8008, 8009, 8014, 8042, 8060, 8069, 8080, 8081,
    8083, 8088, 8090, 8091, 8095, 8118, 8123, 8172, 8181, 8222, 8243, 8280, 8281,
    8333, 8337, 8443, 8500, 8834, 8880, 8888, 8983, 9000, 9001, 9043, 9060, 9080,
    9090, 9091, 9200, 9443, 9502, 9800, 9981, 10000, 10250, 11371, 12443, 15672,
    16080, 17778, 18091, 18092, 20720, 32000, 55440, 55672,
)  # fmt: skip

# administrative and datastore ports whose exposure is the finding
SENSITIVE_PORTS: list[int] = [
    21, 22, 23, 25, 53, 111, 135, 139, 389, 445, 512, 513, 514, 623, 873, 1080,
    1433, 1521, 1723, 2049, 2181, 2375, 2376, 2379, 3306, 3389, 4369, 5432, 5601,
    5672, 5900, 5901, 5984, 6379, 8086, 9042, 9092, 9160, 9200, 9300, 11211,
    15672, 27017, 27018, 50000,
]  # fmt: skip

_TLS_PORTS: frozenset[int] = frozenset(
    {443, 465, 636, 989, 990, 993, 995, 2376, 4443, 5061, 8443, 9443, 12443}
)


class PortProfile(StrEnum):
    WEB = "web"
    EXPOSURE = "exposure"
    TOP_100 = "top-100"
    TOP_1000 = "top-1000"
    FULL = "full"
    CUSTOM = "custom"


@dataclass(frozen=True)
class PortProfileSpec:
    key: str
    label: str
    description: str
    approx: int


PORT_PROFILES: tuple[PortProfileSpec, ...] = (
    PortProfileSpec(
        PortProfile.WEB.value,
        "Web ports",
        "Ports that commonly serve HTTP. Fastest path to the web surface.",
        len(WEB_PORTS),
    ),
    PortProfileSpec(
        PortProfile.EXPOSURE.value,
        "Web and sensitive",
        "Web ports plus remote-access and datastore ports. The default.",
        len(set(WEB_PORTS) | set(SENSITIVE_PORTS)),
    ),
    PortProfileSpec(
        PortProfile.TOP_100.value,
        "Top 100",
        "The 100 most common ports.",
        100,
    ),
    PortProfileSpec(
        PortProfile.TOP_1000.value,
        "Top 1000",
        "The 1,000 most common ports. Slower, broad coverage.",
        1000,
    ),
    PortProfileSpec(
        PortProfile.FULL.value,
        "All ports",
        "Every port from 1 to 65535. Slowest and loudest.",
        MAX_PORT,
    ),
    PortProfileSpec(
        PortProfile.CUSTOM.value,
        "Custom",
        "The list or range set on the stage.",
        0,
    ),
)

EXPOSURE_PORTS: tuple[int, ...] = tuple(sorted(set(WEB_PORTS) | set(SENSITIVE_PORTS)))

# the only ports a CDN edge proxies; scanning past them profiles the CDN, not the target
CDN_EDGE_PORTS: tuple[int, ...] = (
    80, 443, 2052, 2053, 2082, 2083, 2086, 2087, 2095, 2096, 8080, 8443, 8880,
)  # fmt: skip


_WEB_PORT_SET: frozenset[int] = frozenset(WEB_PORTS)
_BY_NAME: dict[str, ServiceSpec] = {}
for _spec in WELL_KNOWN.values():
    _BY_NAME.setdefault(_spec.name, _spec)
_BY_NAME.setdefault("http", _s("http", "HTTP", ServiceClass.WEB, "Web server"))
_BY_NAME.setdefault(
    "https", _s("https", "HTTPS", ServiceClass.WEB, "Web server over TLS", tls=True)
)


# IANA's registry, generated by scripts/fetch_port_registry.py. It is the fallback,
# never the authority: IANA still calls 9200 wap-wsp and 5601 esmagent.
_REGISTRY_PATH = Path(__file__).parent / "data" / "port_registry.json"


@lru_cache(maxsize=1)
def _registry() -> dict[str, list[str]]:
    try:
        return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def registered(port: int) -> tuple[str | None, str]:
    """The IANA service name and description for a port, or (None, "")."""
    entry = _registry().get(str(port))
    if not entry:
        return None, ""
    return entry[0], entry[1] if len(entry) > 1 else ""


def service_for_port(port: int) -> str | None:
    spec = WELL_KNOWN.get(port)
    if spec is not None:
        return spec.name
    if port in _WEB_PORT_SET:
        return "http"
    return registered(port)[0]


def describe(port: int, service: str | None = None) -> tuple[str, bool]:
    """One line on what a port is for, and whether it is only IANA's registration."""
    spec = _spec_for(port, service)
    if spec is not None and spec.description:
        return spec.description, False
    text = registered(port)[1]
    return (text, True) if text else ("", False)


def _spec_for(port: int, service: str | None) -> ServiceSpec | None:
    """The port's own entry unless a banner named something the port does not imply.

    _BY_NAME keeps one spec per name, so consulting it first would give 2376 the
    description of 2375 and tell an operator that Docker over TLS is unauthenticated.
    """
    spec = WELL_KNOWN.get(port)
    if spec is not None and (not service or service == spec.name):
        return spec
    return _BY_NAME.get(service or "") or spec


def service_class(service: str | None, port: int, *, is_http: bool = False) -> str:
    """The one class a service belongs to. HTTP evidence always wins."""
    if is_http:
        return ServiceClass.WEB.value
    spec = _spec_for(port, service)
    if spec is not None:
        return spec.klass
    if port in _WEB_PORT_SET:
        return ServiceClass.WEB.value
    return ServiceClass.OTHER.value


def service_label(service: str | None) -> str:
    named = _BY_NAME.get(service or "")
    return named.label if named else (service or "Unknown")


def likely_tls(port: int) -> bool:
    spec = WELL_KNOWN.get(port)
    return port in _TLS_PORTS or bool(spec and spec.tls)


def profile_ports(profile: str) -> tuple[int, ...] | None:
    """The explicit port list for a profile, or None when the tool expands it itself."""
    if profile == PortProfile.WEB.value:
        return WEB_PORTS
    if profile == PortProfile.EXPOSURE.value:
        return EXPOSURE_PORTS
    return None
