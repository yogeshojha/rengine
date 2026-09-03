from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

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


GROUPS: tuple[str, ...] = ("Host", "HTTP", "Response", "Network", "TLS", "Flags")

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
)

FIELDS_BY_NAME: dict[str, QueryField] = {f.name: f for f in FIELDS}
CANONICAL: dict[str, str] = {
    **{f.name: f.name for f in FIELDS},
    **{alias: f.name for f in FIELDS for alias in f.aliases},
}

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
