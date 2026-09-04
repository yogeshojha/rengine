from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field
from enum import StrEnum

from shared.definitions.ports import (
    PORT_SOURCE_LABELS,
    SERVICE_CLASS_LABELS,
)
from shared.definitions.vulnerabilities import (
    PROTOCOLS,
    SCANNER_LABELS,
    SEVERITY_ORDER,
    VULN_STATES,
)

MAX_QUERY_LENGTH = 2000
MAX_QUERY_NODES = 40
MAX_FREE_TERMS = 8
MAX_NUMBER = 2_147_483_647
COUNT_CAP = 10_000
SNIPPET_RADIUS = 70
SNIPPET_LENGTH = 190


class FieldType(StrEnum):
    STRING = "string"
    ENUM = "enum"
    NUMBER = "number"
    BYTES = "bytes"
    DURATION = "duration"
    DATE = "date"
    IP = "ip"
    TEXT = "text"
    FLAG = "flag"


class Op(StrEnum):
    MATCH = ":"
    EQ = "="
    NE = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    RE = "~"
    NRE = "!~"


_STRING_OPS = (Op.MATCH, Op.EQ, Op.NE, Op.RE, Op.NRE)
_ENUM_OPS = (Op.MATCH, Op.EQ, Op.NE)
_SCALAR_OPS = (Op.MATCH, Op.EQ, Op.NE, Op.GT, Op.GTE, Op.LT, Op.LTE)
_TEXT_OPS = (Op.MATCH, Op.EQ, Op.NE)

OPS_BY_TYPE: dict[FieldType, tuple[Op, ...]] = {
    FieldType.STRING: _STRING_OPS,
    FieldType.ENUM: _ENUM_OPS,
    FieldType.NUMBER: _SCALAR_OPS,
    FieldType.BYTES: _SCALAR_OPS,
    FieldType.DURATION: _SCALAR_OPS,
    FieldType.DATE: _SCALAR_OPS,
    FieldType.IP: _ENUM_OPS,
    FieldType.TEXT: _TEXT_OPS,
    FieldType.FLAG: (Op.MATCH,),
}

OP_HELP: dict[str, str] = {
    ":": "Contains, or equals for numbers and flags",
    "=": "Exact match",
    "!=": "Not equal",
    ">": "Greater than",
    ">=": "Greater than or equal",
    "<": "Less than",
    "<=": "Less than or equal",
    "~": "Matches regular expression",
    "!~": "Does not match regular expression",
}

CONNECTORS: dict[str, str] = {
    "and": "Both sides must match. Two terms side by side already mean and.",
    "or": "Either side may match.",
    "not": "Excludes what follows. A leading - or ! does the same.",
    "( )": "Groups part of a query, as in is:live and (status:403 or status:401).",
    '" "': "Treats the value as one literal phrase.",
    "[a,b]": "Any of the listed values, as in tech:[nginx,apache].",
    "a..b": "Inclusive range, as in status:200..399.",
}


@dataclass(frozen=True)
class QueryField:
    name: str
    type: FieldType
    group: str
    description: str
    example: str
    aliases: tuple[str, ...] = ()
    values: tuple[str, ...] = ()
    facet: str | None = None
    free_text: bool = False
    evidence: str | None = None
    unit: str | None = None
    dynamic_sub: str | None = None


GROUPS: tuple[str, ...] = (
    "Host",
    "HTTP",
    "Response",
    "Network",
    "Certificates",
    "Findings",
    "Flags",
)

CERT_STATES: tuple[str, ...] = ("expired", "expiring", "self-signed", "valid")
STATUS_CLASSES: tuple[str, ...] = ("2xx", "3xx", "4xx", "5xx", "none")

FLAGS: dict[str, str] = {
    "live": "Responded with 2xx or 3xx",
    "web": "Answered on HTTP at all",
    "new": "Absent from the previous scan of this target",
    "resolved": "Resolves to at least one IP",
    "auth": "Login wall or 401/403",
    "cdn": "Served through a CDN",
    "waf": "A WAF was fingerprinted",
    "screenshot": "A screenshot was captured",
    "important": "Flagged important",
    "wildcard": "Matched a wildcard DNS record",
    "issue": "Has a cert, exposure or availability problem",
    "sensitive": "An admin or database port is open",
    "http2": "Negotiated HTTP/2",
    "redirect": "Final URL differs from the probed URL",
    "vulnerable": "A vulnerability scan reported a finding on it",
    "kev": "A known-exploited weakness was found on it",
}

FIELDS: tuple[QueryField, ...] = (
    QueryField(
        name="host",
        type=FieldType.STRING,
        group="Host",
        description="Hostname of the asset.",
        example="host:api",
        aliases=("name", "subdomain"),
        free_text=True,
        evidence="host",
    ),
    QueryField(
        name="url",
        type=FieldType.STRING,
        group="Host",
        description="Probed URL, or the final URL after redirects.",
        example="url:/admin",
        free_text=True,
        evidence="url",
    ),
    QueryField(
        name="path",
        type=FieldType.STRING,
        group="Host",
        description="Path component of the probed URL.",
        example="path:/api/v1",
        evidence="path",
    ),
    QueryField(
        name="cname",
        type=FieldType.STRING,
        group="Host",
        description="CNAME target the host points at.",
        example="cname:s3.amazonaws.com",
        free_text=True,
        evidence="cname",
    ),
    QueryField(
        name="source",
        type=FieldType.ENUM,
        group="Host",
        description="Tool or feed that discovered the host.",
        example="source:crtsh",
        facet="source",
        free_text=True,
        evidence="source",
    ),
    QueryField(
        name="discovered",
        type=FieldType.DATE,
        group="Host",
        description="When the host was first seen in this scan.",
        example="discovered:<7d",
        aliases=("found", "seen"),
    ),
    QueryField(
        name="status",
        type=FieldType.NUMBER,
        group="HTTP",
        description="HTTP status code. Accepts a class such as 4xx.",
        example="status:>=500",
        aliases=("code", "http.status"),
        values=STATUS_CLASSES,
    ),
    QueryField(
        name="title",
        type=FieldType.STRING,
        group="HTTP",
        description="Page title of the response.",
        example='title:"index of"',
        free_text=True,
        evidence="title",
    ),
    QueryField(
        name="server",
        type=FieldType.STRING,
        group="HTTP",
        description="Server header banner.",
        example="server:nginx",
        aliases=("webserver",),
        free_text=True,
        evidence="server",
    ),
    QueryField(
        name="tech",
        type=FieldType.ENUM,
        group="HTTP",
        description="Technology fingerprinted on the response.",
        example="tech:[jenkins,tomcat]",
        facet="tech",
        free_text=True,
        evidence="tech",
    ),
    QueryField(
        name="content_type",
        type=FieldType.STRING,
        group="HTTP",
        description="Content-Type of the response.",
        example="content_type:json",
        aliases=("ctype", "mime"),
        evidence="content_type",
    ),
    QueryField(
        name="size",
        type=FieldType.BYTES,
        group="HTTP",
        description="Response body size. Understands kb and mb.",
        example="size:>500kb",
        aliases=("length", "content_length"),
        unit="bytes",
    ),
    QueryField(
        name="words",
        type=FieldType.NUMBER,
        group="HTTP",
        description="Word count of the response body.",
        example="words:<20",
    ),
    QueryField(
        name="lines",
        type=FieldType.NUMBER,
        group="HTTP",
        description="Line count of the response body.",
        example="lines:>2000",
    ),
    QueryField(
        name="time",
        type=FieldType.DURATION,
        group="HTTP",
        description="Response time. Understands ms and s.",
        example="time:>3s",
        aliases=("rt", "response_time"),
        unit="seconds",
    ),
    QueryField(
        name="redirect",
        type=FieldType.STRING,
        group="HTTP",
        description="Location header the response redirects to.",
        example="redirect:login",
        aliases=("location",),
        free_text=True,
        evidence="redirect",
    ),
    QueryField(
        name="favicon",
        type=FieldType.STRING,
        group="HTTP",
        description="mmh3 favicon hash.",
        example="favicon:-1278323681",
        free_text=True,
        evidence="favicon",
    ),
    QueryField(
        name="body",
        type=FieldType.TEXT,
        group="Response",
        description=(
            "Words in the captured response body. Matches whole words and "
            "prefixes; quote a value to match a phrase."
        ),
        example='body:"internal server"',
        aliases=("response",),
        free_text=True,
        evidence="body",
    ),
    QueryField(
        name="header",
        type=FieldType.TEXT,
        group="Response",
        description=(
            "Words in the response headers. Use header.<name>:<value> to pin "
            "it to one header."
        ),
        example="header.x-powered-by:php",
        aliases=("headers",),
        free_text=True,
        evidence="header",
        dynamic_sub="header name",
    ),
    QueryField(
        name="ip",
        type=FieldType.IP,
        group="Network",
        description="Resolved IP address. Accepts a CIDR range.",
        example="ip:10.0.0.0/8",
        free_text=True,
        evidence="ip",
    ),
    QueryField(
        name="asn",
        type=FieldType.NUMBER,
        group="Network",
        description="Autonomous system number.",
        example="asn:15169",
    ),
    QueryField(
        name="org",
        type=FieldType.STRING,
        group="Network",
        description="Autonomous system owner.",
        example='org:"digital ocean"',
        aliases=("asn_org",),
        free_text=True,
        evidence="org",
    ),
    QueryField(
        name="cdn",
        type=FieldType.STRING,
        group="Network",
        description="CDN in front of the host. yes or no filters on presence.",
        example="cdn:cloudflare",
        free_text=True,
        evidence="cdn",
    ),
    QueryField(
        name="waf",
        type=FieldType.STRING,
        group="Network",
        description="WAF fingerprinted on the host. yes or no filters on presence.",
        example="waf:no",
        free_text=True,
        evidence="waf",
    ),
    QueryField(
        name="port",
        type=FieldType.NUMBER,
        group="Network",
        description="Open port on a resolved IP.",
        example="port:[22,3389]",
    ),
    QueryField(
        name="service",
        type=FieldType.ENUM,
        group="Network",
        description="Service name on an open port.",
        example="service:ssh",
        facet="service",
    ),
    QueryField(
        name="cert",
        type=FieldType.ENUM,
        group="Certificates",
        description="Certificate state.",
        example="cert:expired",
        values=CERT_STATES,
    ),
    QueryField(
        name="cert.cn",
        type=FieldType.STRING,
        group="Certificates",
        description="Certificate subject common name.",
        example="cert.cn:*.internal",
        free_text=True,
        evidence="cert",
    ),
    QueryField(
        name="cert.san",
        type=FieldType.STRING,
        group="Certificates",
        description="Subject alternative name on the certificate.",
        example="cert.san:staging",
        free_text=True,
        evidence="cert",
    ),
    QueryField(
        name="cert.issuer",
        type=FieldType.STRING,
        group="Certificates",
        description="Certificate issuer.",
        example='cert.issuer:"let\'s encrypt"',
        free_text=True,
        evidence="cert",
    ),
    QueryField(
        name="cert.expires",
        type=FieldType.DATE,
        group="Certificates",
        description="Certificate expiry date.",
        example="cert.expires:<30d",
    ),
    QueryField(
        name="tls.version",
        type=FieldType.STRING,
        group="Certificates",
        description="Negotiated TLS version.",
        example="tls.version:tls10",
    ),
    QueryField(
        name="content_hash",
        type=FieldType.STRING,
        group="Response",
        description="Hash of the response body. Identical hashes mean identical content.",
        example="content_hash:8f4e2a",
        aliases=("body_hash",),
    ),
    QueryField(
        name="jarm",
        type=FieldType.STRING,
        group="Certificates",
        description="JARM TLS fingerprint.",
        example="jarm:29d3fd00029d29d0",
    ),
    QueryField(
        name="is",
        type=FieldType.FLAG,
        group="Flags",
        description="Property of the host.",
        example="is:live",
        aliases=("has",),
        values=tuple(FLAGS),
    ),
    QueryField(
        name="vuln",
        type=FieldType.ENUM,
        group="Findings",
        description="Severity of a finding recorded on this host.",
        example="vuln:critical",
        aliases=("finding", "severity"),
        values=SEVERITY_ORDER,
        facet="vuln",
    ),
    QueryField(
        name="cve",
        type=FieldType.STRING,
        group="Findings",
        description="Published vulnerability identifier reported on this host.",
        example="cve:CVE-2021-44228",
    ),
)

EVIDENCE_LABELS: dict[str, str] = {
    "host": "Hostname",
    "url": "URL",
    "path": "Path",
    "cname": "CNAME",
    "source": "Source",
    "title": "Title",
    "server": "Server",
    "tech": "Tech",
    "content_type": "Content type",
    "redirect": "Redirect",
    "favicon": "Favicon",
    "body": "Response body",
    "header": "Response headers",
    "ip": "IP",
    "org": "Network owner",
    "cdn": "CDN",
    "waf": "WAF",
    "cert": "Certificate",
}


@dataclass(frozen=True)
class GroupDimension:
    key: str
    label: str
    description: str


GROUP_DIMENSIONS: tuple[GroupDimension, ...] = (
    GroupDimension(
        key="ip",
        label="IP address",
        description="Names sharing a resolved address",
    ),
    GroupDimension(
        key="favicon",
        label="Favicon",
        description="Names serving the same favicon",
    ),
    GroupDimension(
        key="title",
        label="Page title",
        description="Names serving the same page title",
    ),
    GroupDimension(
        key="cname",
        label="CNAME target",
        description="Names pointing at the same alias",
    ),
    GroupDimension(
        key="tech",
        label="Technology",
        description="Names running the same technology",
    ),
    GroupDimension(
        key="content_hash",
        label="Identical content",
        description="Names serving a byte-identical response",
    ),
    GroupDimension(
        key="jarm",
        label="TLS fingerprint",
        description="Names sharing a JARM TLS fingerprint",
    ),
    GroupDimension(
        key="cert.issuer",
        label="Certificate issuer",
        description="Names whose certificate has the same issuer",
    ),
    GroupDimension(
        key="server",
        label="Server banner",
        description="Names reporting the same server header",
    ),
    GroupDimension(
        key="cdn",
        label="CDN",
        description="Names fronted by the same CDN",
    ),
    GroupDimension(
        key="status",
        label="Status class",
        description="Names by HTTP response class",
    ),
)

MAX_GROUPS = 50


EXAMPLE_GROUPS: tuple[str, ...] = (
    "Takeover risk",
    "Exposed services",
    "Non-production",
    "Access control",
    "Certificates",
    "Origin exposure",
    "Change",
    "Hygiene",
)


@dataclass(frozen=True)
class QueryExample:
    query: str
    description: str
    group: str
    generic: bool = False


EXAMPLES: tuple[QueryExample, ...] = (
    QueryExample(
        query="is:resolved and not is:web",
        description="Resolving hosts with no HTTP service",
        group="Takeover risk",
        generic=True,
    ),
    QueryExample(
        query="cname:. and not is:web",
        description="CNAME records with no HTTP service",
        group="Takeover risk",
    ),
    QueryExample(
        query="cname:elb.amazonaws.com and status:404",
        description="Load balancer aliases returning 404",
        group="Takeover risk",
    ),
    QueryExample(
        query=(
            "cname:[myshopify.com,github.io,herokuapp.com,azurewebsites.net,"
            "netlify.app,pantheonsite.io,wpengine.com,ghost.io]"
        ),
        description="Aliases pointing to third-party hosting",
        group="Takeover risk",
    ),
    QueryExample(
        query="cname:. and not is:resolved",
        description="CNAME records that fail to resolve",
        group="Takeover risk",
    ),
    QueryExample(
        query="is:wildcard",
        description="Hosts matched only by a wildcard record",
        group="Takeover risk",
    ),
    QueryExample(
        query="is:sensitive",
        description="Administrative or database ports exposed",
        group="Exposed services",
    ),
    QueryExample(
        query="port:[3306,5432,27017,6379,9200,11211,5984]",
        description="Database ports reachable from the internet",
        group="Exposed services",
    ),
    QueryExample(
        query="port:[22,23,3389,5900]",
        description="Remote administration ports reachable",
        group="Exposed services",
    ),
    QueryExample(
        query='body:"index of" and status:200',
        description="Directory listings enabled",
        group="Exposed services",
    ),
    QueryExample(
        query=(
            'body:"begin rsa private key" or body:"begin private key" '
            "or body:aws_secret_access_key"
        ),
        description="Private key material in a response body",
        group="Exposed services",
    ),
    QueryExample(
        query='body:traceback or body:"stack trace" or title:exception',
        description="Application stack traces in responses",
        group="Exposed services",
    ),
    QueryExample(
        query='body:"sql syntax" or body:"odbc driver"',
        description="Database error messages in responses",
        group="Exposed services",
    ),
    QueryExample(
        query="title:phpinfo or body:phpinfo",
        description="phpinfo diagnostic pages exposed",
        group="Exposed services",
    ),
    QueryExample(
        query="body:swagger or url:swagger or title:swagger",
        description="API documentation publicly accessible",
        group="Exposed services",
    ),
    QueryExample(
        query=(
            "tech:[jenkins,gitlab,grafana,kibana,prometheus,sonarqube,jira,"
            "confluence] and status:200"
        ),
        description="Developer tooling exposed to the internet",
        group="Exposed services",
    ),
    QueryExample(
        query="host:[jenkins,gitlab,grafana,kibana,jira,confluence,vault,consul]",
        description="Hostnames indicating internal tooling",
        group="Exposed services",
    ),
    QueryExample(
        query="content_type:json and status:200",
        description="JSON endpoints served directly",
        group="Exposed services",
    ),
    QueryExample(
        query="host:[staging,dev,test,uat,qa,sandbox,preprod,demo]",
        description="Non-production hostnames publicly resolvable",
        group="Non-production",
        generic=True,
    ),
    QueryExample(
        query=(
            "host:[staging,dev,test,uat,qa,sandbox,preprod] and is:live and not is:auth"
        ),
        description="Non-production hosts served without authentication",
        group="Non-production",
    ),
    QueryExample(
        query="(host:admin or host:portal or host:console) and is:live and not is:auth",
        description="Administrative interfaces without authentication",
        group="Non-production",
    ),
    QueryExample(
        query="is:auth and is:live",
        description="Authenticated interfaces currently serving",
        group="Access control",
    ),
    QueryExample(
        query="is:auth",
        description="Hosts requiring authentication",
        group="Access control",
    ),
    QueryExample(
        query="header.access-control-allow-origin:*",
        description="Wildcard cross-origin policy on responses",
        group="Access control",
    ),
    QueryExample(
        query="cert:expired and is:live",
        description="Live hosts serving an expired certificate",
        group="Certificates",
    ),
    QueryExample(
        query="cert:expiring",
        description="Certificates expiring within 30 days",
        group="Certificates",
        generic=True,
    ),
    QueryExample(
        query="cert:self-signed",
        description="Self-signed certificates in use",
        group="Certificates",
    ),
    QueryExample(
        query="cert.cn:internal or cert.san:internal or cert.san:local",
        description="Internal hostnames disclosed in certificates",
        group="Certificates",
    ),
    QueryExample(
        query="cert.san:*. and is:live",
        description="Wildcard certificates in use",
        group="Certificates",
    ),
    QueryExample(
        query="tls.version:[tls10,tls11]",
        description="Obsolete TLS versions negotiated",
        group="Certificates",
    ),
    QueryExample(
        query="is:live and not cdn:yes and waf:no",
        description="Hosts served without CDN or WAF",
        group="Origin exposure",
        generic=True,
    ),
    QueryExample(
        query="server:[apache,nginx,iis] and not cdn:yes",
        description="Origin server banners disclosed",
        group="Origin exposure",
    ),
    QueryExample(
        query="header:x-powered-by and not cdn:yes",
        description="Runtime disclosed in response headers",
        group="Origin exposure",
    ),
    QueryExample(
        query="tech:[php,tomcat,jboss,weblogic,coldfusion] and status:200",
        description="Runtimes with significant CVE history",
        group="Origin exposure",
    ),
    QueryExample(
        query="is:new and (status:2xx or status:3xx)",
        description="Newly reachable since the previous scan",
        group="Change",
        generic=True,
    ),
    QueryExample(
        query="is:new and is:auth",
        description="New authenticated interfaces since the previous scan",
        group="Change",
    ),
    QueryExample(
        query="is:new and cert:expired",
        description="New hosts serving an expired certificate",
        group="Change",
    ),
    QueryExample(
        query="is:new",
        description="Hosts absent from the previous scan",
        group="Change",
    ),
    QueryExample(
        query="discovered:<7d and is:live",
        description="Reachable hosts discovered in the last 7 days",
        group="Change",
    ),
    QueryExample(
        query="status:>=500 or title:exception",
        description="Server-side errors returned",
        group="Hygiene",
        generic=True,
    ),
    QueryExample(
        query="not is:resolved",
        description="Hostnames that no longer resolve",
        group="Hygiene",
    ),
    QueryExample(
        query="size:<500 and status:200",
        description="Minimal-content responses returning 200",
        group="Hygiene",
    ),
    QueryExample(
        query="time:>5s",
        description="Responses slower than 5 seconds",
        group="Hygiene",
    ),
    QueryExample(
        query="is:redirect and not is:live",
        description="Redirects terminating in an error",
        group="Hygiene",
    ),
)


@dataclass(frozen=True)
class QueryRegistry:
    key: str
    noun: str
    noun_plural: str
    fields: tuple[QueryField, ...]
    flags: dict[str, str]
    groups: tuple[str, ...]
    dimensions: tuple[GroupDimension, ...]
    examples: tuple[QueryExample, ...]
    example_groups: tuple[str, ...]
    by_name: dict[str, QueryField] = dc_field(init=False, repr=False)
    canonical: dict[str, str] = dc_field(init=False, repr=False)
    dynamic_parent: str | None = dc_field(init=False, repr=False)

    def __post_init__(self) -> None:
        set_ = object.__setattr__
        set_(self, "by_name", {f.name: f for f in self.fields})
        set_(
            self,
            "canonical",
            {
                **{f.name: f.name for f in self.fields},
                **{a: f.name for f in self.fields for a in f.aliases},
            },
        )
        dynamic = next((f.name for f in self.fields if f.dynamic_sub), None)
        set_(self, "dynamic_parent", dynamic)


HOST_QUERY = QueryRegistry(
    key="host",
    noun="host",
    noun_plural="hosts",
    fields=FIELDS,
    flags=FLAGS,
    groups=GROUPS,
    dimensions=GROUP_DIMENSIONS,
    examples=EXAMPLES,
    example_groups=EXAMPLE_GROUPS,
)

IP_GROUPS: tuple[str, ...] = (
    "Address",
    "Network",
    "Services",
    "Hosts",
    "Findings",
    "Flags",
)

IP_FLAGS: dict[str, str] = {
    "alive": "Responded to a probe",
    "open": "One or more ports are open",
    "sensitive": "An admin or database port is open",
    "hosted": "One or more hostnames resolve to it",
    "web": "An HTTP service was probed on it",
    "cdn": "Fronted by a CDN",
    "ptr": "Has a PTR record",
    "private": "In a private address range",
    "v4": "IPv4 address",
    "v6": "IPv6 address",
    "vulnerable": "A vulnerability scan reported a finding on it",
    "kev": "A known-exploited weakness was found on it",
}

IP_EXPOSURE: dict[str, str] = {
    "open": "Open ports",
    "responding": "Responding",
    "quiet": "No response",
}

IP_FIELDS: tuple[QueryField, ...] = (
    QueryField(
        name="ip",
        type=FieldType.IP,
        group="Address",
        description="IP address. Accepts a CIDR range.",
        example="ip:104.16.0.0/12",
        aliases=("address", "addr"),
        free_text=True,
    ),
    QueryField(
        name="ptr",
        type=FieldType.STRING,
        group="Address",
        description="PTR record for the address.",
        example="ptr:.internal",
        aliases=("reverse", "rdns"),
        free_text=True,
    ),
    QueryField(
        name="asn",
        type=FieldType.NUMBER,
        group="Network",
        description="Autonomous system number announcing the address.",
        example="asn:13335",
    ),
    QueryField(
        name="org",
        type=FieldType.STRING,
        group="Network",
        description="Operator of the autonomous system.",
        example='org:"digital ocean"',
        aliases=("asn_org", "operator"),
        free_text=True,
    ),
    QueryField(
        name="country",
        type=FieldType.ENUM,
        group="Network",
        description="Two-letter registered country of the network block.",
        example="country:DE",
        facet="country",
    ),
    QueryField(
        name="prefix",
        type=FieldType.STRING,
        group="Network",
        description="Announced prefix containing the address.",
        example="prefix:104.16",
        free_text=True,
    ),
    QueryField(
        name="cdn",
        type=FieldType.STRING,
        group="Network",
        description="CDN in front of the address. yes or no filters on presence.",
        example="cdn:cloudflare",
        free_text=True,
    ),
    QueryField(
        name="port",
        type=FieldType.NUMBER,
        group="Services",
        description="Open port on the address.",
        example="port:[22,3389]",
        facet="port",
    ),
    QueryField(
        name="service",
        type=FieldType.ENUM,
        group="Services",
        description="Service name on an open port.",
        example="service:ssh",
        facet="service",
        free_text=True,
    ),
    QueryField(
        name="ports",
        type=FieldType.NUMBER,
        group="Services",
        description="Number of open ports on the address.",
        example="ports:>10",
        aliases=("port_count",),
    ),
    QueryField(
        name="host",
        type=FieldType.STRING,
        group="Hosts",
        description="Hostname that resolves to the address.",
        example="host:api",
        aliases=("name", "subdomain"),
        free_text=True,
    ),
    QueryField(
        name="hosts",
        type=FieldType.NUMBER,
        group="Hosts",
        description="Number of hostnames resolving to the address.",
        example="hosts:>5",
        aliases=("host_count",),
    ),
    QueryField(
        name="assets",
        type=FieldType.NUMBER,
        group="Hosts",
        description="Number of HTTP services probed on the address.",
        example="assets:>0",
        aliases=("asset_count",),
    ),
    QueryField(
        name="is",
        type=FieldType.FLAG,
        group="Flags",
        description="Property of the address.",
        example="is:sensitive",
        aliases=("has",),
        values=tuple(IP_FLAGS),
    ),
    QueryField(
        name="vuln",
        type=FieldType.ENUM,
        group="Findings",
        description="Severity of a finding recorded on this address.",
        example="vuln:critical",
        aliases=("finding",),
        values=SEVERITY_ORDER,
    ),
    QueryField(
        name="cve",
        type=FieldType.STRING,
        group="Findings",
        description="Published vulnerability identifier reported on this address.",
        example="cve:CVE-2021-44228",
    ),
)

IP_GROUP_DIMENSIONS: tuple[GroupDimension, ...] = (
    GroupDimension(
        key="asn",
        label="Autonomous system",
        description="Addresses announced by the same AS",
    ),
    GroupDimension(
        key="org",
        label="Network operator",
        description="Addresses run by the same operator",
    ),
    GroupDimension(
        key="prefix",
        label="Announced prefix",
        description="Addresses inside the same announced prefix",
    ),
    GroupDimension(
        key="country",
        label="Country",
        description="Addresses registered in the same country",
    ),
    GroupDimension(
        key="cdn",
        label="CDN",
        description="Addresses fronted by the same CDN",
    ),
    GroupDimension(
        key="port",
        label="Open port",
        description="Addresses exposing the same port",
    ),
    GroupDimension(
        key="service",
        label="Service",
        description="Addresses running the same service",
    ),
)

IP_EXAMPLE_GROUPS: tuple[str, ...] = (
    "Exposed services",
    "Origin exposure",
    "Hosting",
    "Hygiene",
)

IP_EXAMPLES: tuple[QueryExample, ...] = (
    QueryExample(
        query="is:sensitive",
        description="Administrative or database ports exposed",
        group="Exposed services",
        generic=True,
    ),
    QueryExample(
        query="port:[3306,5432,27017,6379,9200,11211,5984]",
        description="Database ports reachable from the internet",
        group="Exposed services",
    ),
    QueryExample(
        query="port:[22,23,3389,5900]",
        description="Remote administration ports reachable",
        group="Exposed services",
    ),
    QueryExample(
        query="service:[ftp,telnet,rlogin,vnc]",
        description="Cleartext remote-access services running",
        group="Exposed services",
    ),
    QueryExample(
        query="ports:>10",
        description="Addresses exposing more than ten ports",
        group="Exposed services",
    ),
    QueryExample(
        query="is:open and not is:cdn",
        description="Open ports on addresses without a CDN",
        group="Origin exposure",
        generic=True,
    ),
    QueryExample(
        query="is:web and not is:cdn",
        description="HTTP served directly from the origin address",
        group="Origin exposure",
    ),
    QueryExample(
        query="is:cdn and is:open",
        description="Open ports on CDN-fronted addresses",
        group="Origin exposure",
    ),
    QueryExample(
        query="hosts:>10",
        description="Addresses shared by more than ten hostnames",
        group="Hosting",
        generic=True,
    ),
    QueryExample(
        query="is:open and not is:hosted",
        description="Open ports on addresses with no hostname",
        group="Hosting",
    ),
    QueryExample(
        query="is:v6",
        description="IPv6 addresses in the attack surface",
        group="Hosting",
    ),
    QueryExample(
        query="is:alive and not is:ptr",
        description="Responding addresses with no PTR record",
        group="Hosting",
    ),
    QueryExample(
        query="is:private",
        description="Private addresses published in public DNS",
        group="Hygiene",
        generic=True,
    ),
    QueryExample(
        query="is:hosted and not is:alive",
        description="Hostnames resolving to an unresponsive address",
        group="Hygiene",
    ),
    QueryExample(
        query="ptr:. and not is:hosted",
        description="Addresses with a PTR record but no known hostname",
        group="Hygiene",
    ),
)

IP_QUERY = QueryRegistry(
    key="ip",
    noun="address",
    noun_plural="addresses",
    fields=IP_FIELDS,
    flags=IP_FLAGS,
    groups=IP_GROUPS,
    dimensions=IP_GROUP_DIMENSIONS,
    examples=IP_EXAMPLES,
    example_groups=IP_EXAMPLE_GROUPS,
)

SERVICE_GROUPS: tuple[str, ...] = (
    "Service",
    "Software",
    "Address",
    "Hosts",
    "Findings",
    "Flags",
)

SERVICE_FLAGS: dict[str, str] = {
    "new": "Not open in an earlier scan of this target",
    "http": "Answered an HTTP request",
    "tls": "Negotiates TLS",
    "sensitive": "An administrative or datastore port",
    "named": "Software identified",
    "passive": "Reported by an internet-wide scanner, not confirmed by this scan",
    "confirmed": "Observed directly by this scan",
    "cdn": "On a CDN-fronted address",
    "hosted": "A hostname resolves to the address",
    "private": "In a private address range",
    "v4": "IPv4 address",
    "v6": "IPv6 address",
    "vulnerable": "A vulnerability scan reported a finding on it",
    "kev": "A known-exploited weakness was found on it",
}

SERVICE_EXPOSURE: dict[str, str] = dict(SERVICE_CLASS_LABELS)

SERVICE_FIELDS: tuple[QueryField, ...] = (
    QueryField(
        name="port",
        type=FieldType.NUMBER,
        group="Service",
        description="Port number. Accepts a list or a range.",
        example="port:[22,3389]",
        facet="port",
    ),
    QueryField(
        name="service",
        type=FieldType.STRING,
        group="Service",
        description="Service running on the port.",
        example="service:ssh",
        facet="service",
        free_text=True,
    ),
    QueryField(
        name="class",
        type=FieldType.ENUM,
        group="Service",
        description="Service class.",
        example="class:database",
        aliases=("kind",),
        values=tuple(SERVICE_EXPOSURE),
        facet="class",
    ),
    QueryField(
        name="protocol",
        type=FieldType.ENUM,
        group="Service",
        description="Transport protocol.",
        example="protocol:tcp",
        values=("tcp", "udp"),
    ),
    QueryField(
        name="source",
        type=FieldType.ENUM,
        group="Service",
        description="How the service was observed.",
        example="source:naabu",
        values=tuple(PORT_SOURCE_LABELS),
        facet="source",
    ),
    QueryField(
        name="product",
        type=FieldType.STRING,
        group="Software",
        description="Software named by the service banner.",
        example="product:OpenSSH",
        free_text=True,
    ),
    QueryField(
        name="version",
        type=FieldType.STRING,
        group="Software",
        description="Version reported by the service.",
        example="version:8.9",
        free_text=True,
    ),
    QueryField(
        name="banner",
        type=FieldType.TEXT,
        group="Software",
        description="Text the service returned on connect.",
        example="banner:ubuntu",
        free_text=True,
    ),
    QueryField(
        name="ip",
        type=FieldType.IP,
        group="Address",
        description="Address the service listens on. Accepts a CIDR range.",
        example="ip:104.16.0.0/12",
        aliases=("address", "addr"),
        free_text=True,
    ),
    QueryField(
        name="asn",
        type=FieldType.NUMBER,
        group="Address",
        description="Autonomous system announcing the address.",
        example="asn:13335",
        facet="asn",
    ),
    QueryField(
        name="org",
        type=FieldType.STRING,
        group="Address",
        description="Operator of the announcing network.",
        example="org:cloudflare",
        aliases=("as_name", "asn_org"),
        free_text=True,
    ),
    QueryField(
        name="country",
        type=FieldType.ENUM,
        group="Address",
        description="Two-letter country of the address.",
        example="country:DE",
        facet="country",
    ),
    QueryField(
        name="cdn",
        type=FieldType.STRING,
        group="Address",
        description="CDN in front of the address. yes or no filters on presence.",
        example="cdn:cloudflare",
        free_text=True,
    ),
    QueryField(
        name="host",
        type=FieldType.STRING,
        group="Hosts",
        description="Hostname resolving to the address.",
        example="host:api",
        aliases=("name", "subdomain"),
        free_text=True,
    ),
    QueryField(
        name="status",
        type=FieldType.NUMBER,
        group="Hosts",
        description="HTTP status returned on this port.",
        example="status:200",
    ),
    QueryField(
        name="is",
        type=FieldType.FLAG,
        group="Flags",
        description="Property of the service.",
        example="is:sensitive",
        aliases=("has",),
        values=tuple(SERVICE_FLAGS),
    ),
    QueryField(
        name="vuln",
        type=FieldType.ENUM,
        group="Findings",
        description="Severity of a finding recorded on this service.",
        example="vuln:critical",
        aliases=("finding",),
        values=SEVERITY_ORDER,
    ),
    QueryField(
        name="cve",
        type=FieldType.STRING,
        group="Findings",
        description="Published vulnerability identifier reported on this service.",
        example="cve:CVE-2021-44228",
    ),
)

SERVICE_GROUP_DIMENSIONS: tuple[GroupDimension, ...] = (
    GroupDimension(
        key="service",
        label="Service",
        description="Ports running the same service",
    ),
    GroupDimension(
        key="class",
        label="Service class",
        description="Services of the same class",
    ),
    GroupDimension(
        key="port",
        label="Port",
        description="Services on the same port number",
    ),
    GroupDimension(
        key="product",
        label="Software",
        description="Services running the same software",
    ),
    GroupDimension(
        key="ip",
        label="Address",
        description="Services on the same address",
    ),
    GroupDimension(
        key="asn",
        label="Autonomous system",
        description="Services in the same announced network",
    ),
    GroupDimension(
        key="org",
        label="Network operator",
        description="Services on the same operator's network",
    ),
    GroupDimension(
        key="country",
        label="Country",
        description="Services in the same country",
    ),
    GroupDimension(
        key="source",
        label="Evidence",
        description="Services with the same evidence",
    ),
)

SERVICE_EXAMPLE_GROUPS: tuple[str, ...] = (
    "Critical exposure",
    "Change",
    "Remote access",
    "Web surface",
    "Evidence",
    "Hygiene",
)

SERVICE_EXAMPLES: tuple[QueryExample, ...] = (
    QueryExample(
        query="class:database",
        description="Data stores reachable from the internet",
        group="Critical exposure",
        generic=True,
    ),
    QueryExample(
        query="service:[redis,memcached,mongodb,elasticsearch]",
        description="Data stores with no authentication by default",
        group="Critical exposure",
    ),
    QueryExample(
        query="service:docker",
        description="Container runtime API exposed",
        group="Critical exposure",
    ),
    QueryExample(
        query="is:sensitive and not is:cdn",
        description="Administrative ports on an origin address",
        group="Critical exposure",
    ),
    QueryExample(
        query="is:new",
        description="Ports that were closed at the previous scan",
        group="Change",
        generic=True,
    ),
    QueryExample(
        query="is:new and is:sensitive",
        description="Administrative ports opened since the previous scan",
        group="Change",
    ),
    QueryExample(
        query="class:remote",
        description="Interactive administration reachable",
        group="Remote access",
        generic=True,
    ),
    QueryExample(
        query="service:ssh and not port:22",
        description="SSH on a non-standard port",
        group="Remote access",
    ),
    QueryExample(
        query="service:[telnet,ftp,rlogin,rexec]",
        description="Protocols that carry credentials in the clear",
        group="Remote access",
    ),
    QueryExample(
        query="service:rdp or service:vnc",
        description="Remote desktop reachable from the internet",
        group="Remote access",
    ),
    QueryExample(
        query="is:http and not port:[80,443]",
        description="Web services on a non-standard port",
        group="Web surface",
        generic=True,
    ),
    QueryExample(
        query="is:http and not is:tls",
        description="Web services without TLS",
        group="Web surface",
    ),
    QueryExample(
        query="class:web and not is:http",
        description="Web ports with no HTTP response",
        group="Web surface",
    ),
    QueryExample(
        query="status:401 or status:403",
        description="Services behind a login wall",
        group="Web surface",
    ),
    QueryExample(
        query="is:passive",
        description="Ports reported by external scanners, not confirmed",
        group="Evidence",
        generic=True,
    ),
    QueryExample(
        query="is:named",
        description="Services with identified software",
        group="Evidence",
        generic=True,
    ),
    QueryExample(
        query="is:confirmed and not is:named",
        description="Open ports with no service identified",
        group="Evidence",
    ),
    QueryExample(
        query="class:mail and not is:tls",
        description="Mail services without transport encryption",
        group="Hygiene",
    ),
    QueryExample(
        query="not is:hosted",
        description="Services on addresses with no known hostname",
        group="Hygiene",
    ),
    QueryExample(
        query="class:infra",
        description="Directory, file and management services",
        group="Hygiene",
        generic=True,
    ),
)

SERVICE_QUERY = QueryRegistry(
    key="service",
    noun="service",
    noun_plural="services",
    fields=SERVICE_FIELDS,
    flags=SERVICE_FLAGS,
    groups=SERVICE_GROUPS,
    dimensions=SERVICE_GROUP_DIMENSIONS,
    examples=SERVICE_EXAMPLES,
    example_groups=SERVICE_EXAMPLE_GROUPS,
)


VULN_GROUPS: tuple[str, ...] = (
    "Finding",
    "Classification",
    "Asset",
    "Review",
    "Flags",
)

VULN_FLAGS: dict[str, str] = {
    "new": "Not reported by an earlier scan of this target",
    "kev": "Listed as exploited in the wild",
    "cve": "Carries a published vulnerability identifier",
    "exploitable": "Known exploited, or above the EPSS threshold",
    "corroborated": "A second check at the same location names the same CVE or weakness class",
    "proven": "The request and response that produced it were stored",
    "extracted": "The check pulled a value out of the response",
    "web": "Found on an HTTP asset",
    "cdn": "On an asset served through a CDN",
    "triaged": "Reviewed by someone",
    "open": "Not yet reviewed",
    "suppressed": "Reviewed and set aside as a false positive or accepted risk",
}

VULN_FIELDS: tuple[QueryField, ...] = (
    QueryField(
        name="name",
        type=FieldType.STRING,
        group="Finding",
        description="Title of the check that fired.",
        example="name:log4j",
        aliases=("title",),
        free_text=True,
        evidence="name",
    ),
    QueryField(
        name="template",
        type=FieldType.STRING,
        group="Finding",
        description="Identifier of the check that fired.",
        example="template:CVE-2021-44228",
        aliases=("check", "rule", "id"),
        facet="template",
        free_text=True,
        evidence="template",
    ),
    QueryField(
        name="severity",
        type=FieldType.ENUM,
        group="Finding",
        description="Severity the check declares.",
        example="severity:[critical,high]",
        aliases=("sev",),
        values=SEVERITY_ORDER,
        facet="severity",
    ),
    QueryField(
        name="type",
        type=FieldType.ENUM,
        group="Finding",
        description="Protocol the check speaks.",
        example="type:ssl",
        aliases=("protocol",),
        values=PROTOCOLS,
        facet="protocol",
    ),
    QueryField(
        name="scanner",
        type=FieldType.ENUM,
        group="Finding",
        description="Tool that produced the finding.",
        example="scanner:nuclei",
        values=tuple(SCANNER_LABELS),
        facet="scanner",
    ),
    QueryField(
        name="tag",
        type=FieldType.STRING,
        group="Finding",
        description="Tag carried by the check.",
        example="tag:takeover",
        aliases=("tags",),
        facet="tag",
    ),
    QueryField(
        name="matcher",
        type=FieldType.STRING,
        group="Finding",
        description="Named matcher inside the check that fired.",
        example="matcher:unauthenticated",
    ),
    QueryField(
        name="extracted",
        type=FieldType.STRING,
        group="Finding",
        description="Value the check pulled out of the response.",
        example="extracted:admin",
        free_text=True,
        evidence="extracted",
    ),
    QueryField(
        name="author",
        type=FieldType.STRING,
        group="Finding",
        description="Author of the check.",
        example="author:pdteam",
    ),
    QueryField(
        name="cve",
        type=FieldType.STRING,
        group="Classification",
        description="Published vulnerability identifier.",
        example="cve:CVE-2021-44228",
        facet="cve",
        free_text=True,
        evidence="cve",
    ),
    QueryField(
        name="cwe",
        type=FieldType.STRING,
        group="Classification",
        description="Weakness class.",
        example="cwe:CWE-89",
    ),
    QueryField(
        name="cvss",
        type=FieldType.NUMBER,
        group="Classification",
        description="CVSS base score.",
        example="cvss>=9",
    ),
    QueryField(
        name="epss",
        type=FieldType.NUMBER,
        group="Classification",
        description="Probability of exploitation in the next 30 days, 0 to 1.",
        example="epss>=0.5",
    ),
    QueryField(
        name="host",
        type=FieldType.STRING,
        group="Asset",
        description="Hostname the finding sits on.",
        example="host:api",
        aliases=("name.host", "subdomain"),
        facet="host",
        free_text=True,
        evidence="host",
    ),
    QueryField(
        name="location",
        type=FieldType.STRING,
        group="Asset",
        description="Exact place the check matched.",
        example="location:/actuator",
        aliases=("matched", "url", "path"),
        free_text=True,
        evidence="location",
    ),
    QueryField(
        name="ip",
        type=FieldType.IP,
        group="Asset",
        description="Address behind the finding. Accepts a CIDR range.",
        example="ip:104.16.0.0/12",
        aliases=("address", "addr"),
    ),
    QueryField(
        name="port",
        type=FieldType.NUMBER,
        group="Asset",
        description="Port the finding is on.",
        example="port:8080",
    ),
    QueryField(
        name="status",
        type=FieldType.NUMBER,
        group="Asset",
        description="HTTP status the asset returned to this scan.",
        example="status:200",
    ),
    QueryField(
        name="tech",
        type=FieldType.STRING,
        group="Asset",
        description="Technology fingerprinted on the asset.",
        example="tech:nginx",
    ),
    QueryField(
        name="asn",
        type=FieldType.NUMBER,
        group="Asset",
        description="Autonomous system announcing the address.",
        example="asn:13335",
    ),
    QueryField(
        name="country",
        type=FieldType.ENUM,
        group="Asset",
        description="Two-letter country of the address.",
        example="country:DE",
    ),
    QueryField(
        name="state",
        type=FieldType.ENUM,
        group="Review",
        description="Review decision recorded for this finding.",
        example="state:false_positive",
        values=VULN_STATES,
        facet="state",
    ),
    QueryField(
        name="seen",
        type=FieldType.DATE,
        group="Review",
        description="When this scan recorded the finding.",
        example="seen:<24h",
        aliases=("discovered", "age"),
    ),
    QueryField(
        name="is",
        type=FieldType.FLAG,
        group="Flags",
        description="Property of the finding.",
        example="is:kev",
        aliases=("has",),
        values=tuple(VULN_FLAGS),
    ),
)

VULN_GROUP_DIMENSIONS: tuple[GroupDimension, ...] = (
    GroupDimension(
        key="template",
        label="Check",
        description="The same weakness across every asset it was found on",
    ),
    GroupDimension(
        key="severity",
        label="Severity",
        description="Findings of the same severity",
    ),
    GroupDimension(
        key="location",
        label="Location",
        description="Every check that fired at the same place",
    ),
    GroupDimension(
        key="host",
        label="Host",
        description="Everything found on one hostname",
    ),
    GroupDimension(
        key="tag",
        label="Category",
        description="Findings the checks categorise the same way",
    ),
    GroupDimension(
        key="cve",
        label="CVE",
        description="Findings sharing a published identifier",
    ),
    GroupDimension(
        key="type",
        label="Protocol",
        description="Findings on the same protocol",
    ),
    GroupDimension(
        key="state",
        label="Review state",
        description="Findings at the same point in review",
    ),
    GroupDimension(
        key="port",
        label="Port",
        description="Findings on the same port",
    ),
    GroupDimension(
        key="scanner",
        label="Scanner",
        description="Findings from the same tool",
    ),
)

VULN_EXAMPLE_GROUPS: tuple[str, ...] = (
    "Act on this first",
    "Change",
    "Access control",
    "Data exposure",
    "Infrastructure",
    "Review",
)

VULN_EXAMPLES: tuple[QueryExample, ...] = (
    QueryExample(
        query="is:kev",
        description="Weaknesses with confirmed exploitation in the wild",
        group="Act on this first",
        generic=True,
    ),
    QueryExample(
        query="severity:critical",
        description="Findings rated critical",
        group="Act on this first",
        generic=True,
    ),
    QueryExample(
        query="is:corroborated",
        description="Findings a second check confirms at the same location",
        group="Act on this first",
        generic=True,
    ),
    QueryExample(
        query="is:corroborated and severity:[critical,high]",
        description="Severe findings that more than one check agrees on",
        group="Act on this first",
    ),
    QueryExample(
        query="is:exploitable and not is:suppressed",
        description="Exploited or likely to be, and still open",
        group="Act on this first",
    ),
    QueryExample(
        query="severity:[critical,high] and not is:cdn",
        description="Severe findings on origin infrastructure",
        group="Act on this first",
    ),
    QueryExample(
        query="cvss>=9",
        description="Findings scored 9.0 or above",
        group="Act on this first",
    ),
    QueryExample(
        query="is:new",
        description="Findings absent from the previous scan of this target",
        group="Change",
        generic=True,
    ),
    QueryExample(
        query="is:new and severity:[critical,high]",
        description="Severe findings that appeared since the previous scan",
        group="Change",
    ),
    QueryExample(
        query="seen:<24h and is:cve",
        description="Published vulnerabilities recorded in the last day",
        group="Change",
    ),
    QueryExample(
        query="tag:default-login",
        description="Accounts still on the credentials they shipped with",
        group="Access control",
        generic=True,
    ),
    QueryExample(
        query="tag:panel and severity:[critical,high,medium]",
        description="Administrative interfaces reachable from the internet",
        group="Access control",
    ),
    QueryExample(
        query="tag:[unauth,auth-bypass]",
        description="Protected functionality reachable without credentials",
        group="Access control",
    ),
    QueryExample(
        query="tag:[exposure,disclosure]",
        description="Files and data served that were not meant to be public",
        group="Data exposure",
        generic=True,
    ),
    QueryExample(
        query="tag:[backup,config,files]",
        description="Source, configuration and backups reachable over HTTP",
        group="Data exposure",
    ),
    QueryExample(
        query="is:extracted",
        description="Findings that pulled a concrete value out of the response",
        group="Data exposure",
    ),
    QueryExample(
        query="tag:takeover",
        description="Names pointing at infrastructure someone else can claim",
        group="Infrastructure",
        generic=True,
    ),
    QueryExample(
        query="type:ssl",
        description="Transport security defects",
        group="Infrastructure",
    ),
    QueryExample(
        query="type:[network,dns]",
        description="Findings outside the web surface",
        group="Infrastructure",
    ),
    QueryExample(
        query="tag:misconfig",
        description="Services left in a state their operator did not intend",
        group="Infrastructure",
    ),
    QueryExample(
        query="is:open and severity:[critical,high]",
        description="Severe findings nobody has reviewed yet",
        group="Review",
        generic=True,
    ),
    QueryExample(
        query="state:false_positive",
        description="Findings a reviewer rejected",
        group="Review",
    ),
    QueryExample(
        query="is:triaged",
        description="Findings someone has already decided on",
        group="Review",
    ),
)

VULN_QUERY = QueryRegistry(
    key="vulnerability",
    noun="finding",
    noun_plural="findings",
    fields=VULN_FIELDS,
    flags=VULN_FLAGS,
    groups=VULN_GROUPS,
    dimensions=VULN_GROUP_DIMENSIONS,
    examples=VULN_EXAMPLES,
    example_groups=VULN_EXAMPLE_GROUPS,
)
