"""Ports, services and exposure classes — the SSOT for the scan pipeline and the query layer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

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

SERVICE_CLASS_HELP: dict[str, str] = {
    ServiceClass.WEB.value: "Answered an HTTP request, or listens on a web port",
    ServiceClass.REMOTE.value: "Interactive administration: SSH, RDP, VNC, Telnet",
    ServiceClass.DATABASE.value: "Databases, caches and search clusters",
    ServiceClass.MAIL.value: "SMTP, IMAP and POP endpoints",
    ServiceClass.INFRA.value: "Directory, file, name and management services",
    ServiceClass.OTHER.value: "Listening, not yet attributed to a known service",
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
    PortSource.INTERNETDB.value: "Known exposure",
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
    tls: bool = False


def _s(name: str, label: str, klass: ServiceClass, *, tls: bool = False) -> ServiceSpec:
    return ServiceSpec(name=name, label=label, klass=klass.value, tls=tls)


# port -> canonical service. Keep names lowercase and stable: they are query values.
WELL_KNOWN: dict[int, ServiceSpec] = {
    21: _s("ftp", "FTP", ServiceClass.INFRA),
    22: _s("ssh", "SSH", ServiceClass.REMOTE),
    23: _s("telnet", "Telnet", ServiceClass.REMOTE),
    25: _s("smtp", "SMTP", ServiceClass.MAIL),
    53: _s("dns", "DNS", ServiceClass.INFRA),
    69: _s("tftp", "TFTP", ServiceClass.INFRA),
    88: _s("kerberos", "Kerberos", ServiceClass.INFRA),
    110: _s("pop3", "POP3", ServiceClass.MAIL),
    111: _s("rpcbind", "RPC portmapper", ServiceClass.INFRA),
    135: _s("msrpc", "MSRPC", ServiceClass.INFRA),
    137: _s("netbios", "NetBIOS", ServiceClass.INFRA),
    139: _s("netbios-ssn", "NetBIOS session", ServiceClass.INFRA),
    143: _s("imap", "IMAP", ServiceClass.MAIL),
    161: _s("snmp", "SNMP", ServiceClass.INFRA),
    389: _s("ldap", "LDAP", ServiceClass.INFRA),
    427: _s("slp", "SLP", ServiceClass.INFRA),
    445: _s("smb", "SMB", ServiceClass.INFRA),
    465: _s("smtps", "SMTPS", ServiceClass.MAIL, tls=True),
    500: _s("isakmp", "IKE", ServiceClass.INFRA),
    512: _s("rexec", "rexec", ServiceClass.REMOTE),
    513: _s("rlogin", "rlogin", ServiceClass.REMOTE),
    514: _s("syslog", "Syslog", ServiceClass.INFRA),
    515: _s("printer", "LPD", ServiceClass.INFRA),
    548: _s("afp", "AFP", ServiceClass.INFRA),
    554: _s("rtsp", "RTSP", ServiceClass.OTHER),
    587: _s("smtp", "SMTP submission", ServiceClass.MAIL),
    623: _s("ipmi", "IPMI", ServiceClass.INFRA),
    636: _s("ldaps", "LDAPS", ServiceClass.INFRA, tls=True),
    873: _s("rsync", "rsync", ServiceClass.INFRA),
    993: _s("imaps", "IMAPS", ServiceClass.MAIL, tls=True),
    995: _s("pop3s", "POP3S", ServiceClass.MAIL, tls=True),
    1080: _s("socks", "SOCKS proxy", ServiceClass.INFRA),
    1433: _s("mssql", "Microsoft SQL Server", ServiceClass.DATABASE),
    1521: _s("oracle", "Oracle DB", ServiceClass.DATABASE),
    1723: _s("pptp", "PPTP", ServiceClass.REMOTE),
    2049: _s("nfs", "NFS", ServiceClass.INFRA),
    2181: _s("zookeeper", "ZooKeeper", ServiceClass.INFRA),
    2375: _s("docker", "Docker API", ServiceClass.INFRA),
    2376: _s("docker", "Docker API", ServiceClass.INFRA, tls=True),
    2379: _s("etcd", "etcd", ServiceClass.DATABASE),
    3128: _s("http-proxy", "HTTP proxy", ServiceClass.WEB),
    3268: _s("ldap", "Global catalog", ServiceClass.INFRA),
    3306: _s("mysql", "MySQL", ServiceClass.DATABASE),
    3389: _s("rdp", "RDP", ServiceClass.REMOTE),
    4369: _s("epmd", "Erlang port mapper", ServiceClass.INFRA),
    4444: _s("metasploit", "Metasploit", ServiceClass.OTHER),
    5060: _s("sip", "SIP", ServiceClass.OTHER),
    5222: _s("xmpp", "XMPP", ServiceClass.OTHER),
    5353: _s("mdns", "mDNS", ServiceClass.INFRA),
    5432: _s("postgresql", "PostgreSQL", ServiceClass.DATABASE),
    5672: _s("amqp", "AMQP", ServiceClass.INFRA),
    5900: _s("vnc", "VNC", ServiceClass.REMOTE),
    5901: _s("vnc", "VNC", ServiceClass.REMOTE),
    5984: _s("couchdb", "CouchDB", ServiceClass.DATABASE),
    6379: _s("redis", "Redis", ServiceClass.DATABASE),
    7001: _s("weblogic", "WebLogic", ServiceClass.WEB),
    7199: _s("cassandra", "Cassandra JMX", ServiceClass.DATABASE),
    8086: _s("influxdb", "InfluxDB", ServiceClass.DATABASE),
    9042: _s("cassandra", "Cassandra", ServiceClass.DATABASE),
    9092: _s("kafka", "Kafka", ServiceClass.INFRA),
    9160: _s("cassandra", "Cassandra Thrift", ServiceClass.DATABASE),
    9200: _s("elasticsearch", "Elasticsearch", ServiceClass.DATABASE),
    9300: _s("elasticsearch", "Elasticsearch transport", ServiceClass.DATABASE),
    11211: _s("memcached", "Memcached", ServiceClass.DATABASE),
    27017: _s("mongodb", "MongoDB", ServiceClass.DATABASE),
    27018: _s("mongodb", "MongoDB shard", ServiceClass.DATABASE),
    50000: _s("db2", "IBM Db2", ServiceClass.DATABASE),
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

PORT_PROFILE_KEYS: tuple[str, ...] = tuple(p.key for p in PORT_PROFILES)

EXPOSURE_PORTS: tuple[int, ...] = tuple(sorted(set(WEB_PORTS) | set(SENSITIVE_PORTS)))

# the only ports a CDN edge proxies; scanning past them profiles the CDN, not the target
CDN_EDGE_PORTS: tuple[int, ...] = (
    80, 443, 2052, 2053, 2082, 2083, 2086, 2087, 2095, 2096, 8080, 8443, 8880,
)  # fmt: skip


_WEB_PORT_SET: frozenset[int] = frozenset(WEB_PORTS)
_SENSITIVE_PORT_SET: frozenset[int] = frozenset(SENSITIVE_PORTS)
_BY_NAME: dict[str, ServiceSpec] = {}
for _spec in WELL_KNOWN.values():
    _BY_NAME.setdefault(_spec.name, _spec)
_BY_NAME.setdefault("http", _s("http", "HTTP", ServiceClass.WEB))
_BY_NAME.setdefault("https", _s("https", "HTTPS", ServiceClass.WEB, tls=True))


def service_for_port(port: int) -> str | None:
    spec = WELL_KNOWN.get(port)
    if spec is not None:
        return spec.name
    return "http" if port in _WEB_PORT_SET else None


def service_class(service: str | None, port: int, *, is_http: bool = False) -> str:
    """The one class a service belongs to. HTTP evidence always wins."""
    if is_http:
        return ServiceClass.WEB.value
    named = _BY_NAME.get(service or "")
    if named is not None:
        return named.klass
    spec = WELL_KNOWN.get(port)
    if spec is not None:
        return spec.klass
    if port in _WEB_PORT_SET:
        return ServiceClass.WEB.value
    return ServiceClass.OTHER.value


def service_label(service: str | None) -> str:
    named = _BY_NAME.get(service or "")
    return named.label if named else (service or "Unknown")


def is_sensitive(port: int) -> bool:
    return port in _SENSITIVE_PORT_SET


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
