from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import parse_qsl, urlsplit

MAX_ENDPOINTS_PER_SCAN = 200_000
MAX_URL_LENGTH = 2000
MAX_PATH_LENGTH = 1500
MAX_HOST_LENGTH = 500
MAX_FILENAME_LENGTH = 300
MAX_PARAMS = 40
MAX_PARAM_SAMPLES = 10
MAX_DEPTH = 30
MAX_TREE_NODES = 5000
MAX_TREE_ROWS = 60_000
DEFAULT_PROBE_CAP = 5000


class CrawlScope(StrEnum):
    """katana -field-scope; anything else is read by katana as a custom regex."""

    DN = "dn"
    RDN = "rdn"
    FQDN = "fqdn"


CRAWL_SCOPES: dict[str, str] = {
    CrawlScope.DN.value: "Same domain name",
    CrawlScope.RDN.value: "Same registrable domain and its subdomains",
    CrawlScope.FQDN.value: "Only the exact hostname",
}


class SourceKind(StrEnum):
    PASSIVE = "passive"
    ACTIVE = "active"
    DERIVED = "derived"


class EndpointSource(StrEnum):
    SEED = "seed"
    RESPONSE_MINING = "response_mining"
    CRAWL = "crawl"
    ROBOTS = "robots"
    SITEMAP = "sitemap"
    ARCHIVE = "archive"
    DEEP_ARCHIVE = "deep_archive"
    JS = "js"
    FUZZ = "fuzz"
    PARAM_MINING = "param_mining"
    VULN_SCAN = "vuln_scan"
    IMPORT = "import"
    OTHER = "other"


SOURCE_LABELS: dict[str, str] = {
    EndpointSource.SEED.value: "Site root",
    EndpointSource.RESPONSE_MINING.value: "Response mining",
    EndpointSource.CRAWL.value: "Crawl",
    EndpointSource.ROBOTS.value: "robots.txt",
    EndpointSource.SITEMAP.value: "sitemap.xml",
    EndpointSource.ARCHIVE.value: "Archive",
    EndpointSource.DEEP_ARCHIVE.value: "Deep archive",
    EndpointSource.JS.value: "JavaScript",
    EndpointSource.FUZZ.value: "Content discovery",
    EndpointSource.PARAM_MINING.value: "Parameter mining",
    EndpointSource.VULN_SCAN.value: "Vulnerability scan",
    EndpointSource.IMPORT.value: "Imported",
    EndpointSource.OTHER.value: "Other",
}

SOURCE_HELP: dict[str, str] = {
    EndpointSource.SEED.value: "The web asset itself, as the HTTP probe recorded it.",
    EndpointSource.RESPONSE_MINING.value: "Extracted from a response body this scan already stored. No extra request was sent.",
    EndpointSource.CRAWL.value: "Reached by following links from a page on this host.",
    EndpointSource.ROBOTS.value: "Listed in the site's own robots.txt.",
    EndpointSource.SITEMAP.value: "Listed in the site's own sitemap.",
    EndpointSource.ARCHIVE.value: "Recorded by a public archive. It may no longer exist.",
    EndpointSource.DEEP_ARCHIVE.value: "Recorded by a deep archive sweep. It may no longer exist.",
    EndpointSource.JS.value: "Extracted from a JavaScript bundle or its source map.",
    EndpointSource.FUZZ.value: "Guessed from a wordlist and answered.",
    EndpointSource.PARAM_MINING.value: "A parameter the endpoint accepts but did not advertise.",
    EndpointSource.VULN_SCAN.value: "A location a vulnerability scanner reported.",
    EndpointSource.IMPORT.value: "Supplied by a user.",
    EndpointSource.OTHER.value: "Source not recorded.",
}

SOURCE_KIND: dict[str, str] = {
    EndpointSource.SEED.value: SourceKind.DERIVED.value,
    EndpointSource.RESPONSE_MINING.value: SourceKind.DERIVED.value,
    EndpointSource.CRAWL.value: SourceKind.ACTIVE.value,
    EndpointSource.ROBOTS.value: SourceKind.ACTIVE.value,
    EndpointSource.SITEMAP.value: SourceKind.ACTIVE.value,
    EndpointSource.ARCHIVE.value: SourceKind.PASSIVE.value,
    EndpointSource.DEEP_ARCHIVE.value: SourceKind.PASSIVE.value,
    EndpointSource.JS.value: SourceKind.ACTIVE.value,
    EndpointSource.FUZZ.value: SourceKind.ACTIVE.value,
    EndpointSource.PARAM_MINING.value: SourceKind.ACTIVE.value,
    EndpointSource.VULN_SCAN.value: SourceKind.DERIVED.value,
    EndpointSource.IMPORT.value: SourceKind.DERIVED.value,
    EndpointSource.OTHER.value: SourceKind.DERIVED.value,
}

# how strongly a source asserts the endpoint exists right now; drives merge precedence
SOURCE_RANK: dict[str, int] = {
    EndpointSource.OTHER.value: 0,
    EndpointSource.ARCHIVE.value: 10,
    EndpointSource.DEEP_ARCHIVE.value: 10,
    EndpointSource.IMPORT.value: 15,
    EndpointSource.JS.value: 20,
    EndpointSource.RESPONSE_MINING.value: 25,
    EndpointSource.ROBOTS.value: 30,
    EndpointSource.SITEMAP.value: 30,
    EndpointSource.PARAM_MINING.value: 35,
    EndpointSource.VULN_SCAN.value: 40,
    EndpointSource.FUZZ.value: 45,
    EndpointSource.CRAWL.value: 50,
    EndpointSource.SEED.value: 60,
}

ARCHIVE_SOURCES: frozenset[str] = frozenset(
    {EndpointSource.ARCHIVE.value, EndpointSource.DEEP_ARCHIVE.value}
)

# a source that proves the endpoint was linked from somewhere on the live site
LINKED_SOURCES: frozenset[str] = frozenset(
    {
        EndpointSource.CRAWL.value,
        EndpointSource.RESPONSE_MINING.value,
        EndpointSource.SITEMAP.value,
        EndpointSource.JS.value,
    }
)

PASSIVE_SOURCES: frozenset[str] = frozenset(
    s for s, kind in SOURCE_KIND.items() if kind != SourceKind.ACTIVE.value
)


# the verification pass reports coverage but never discovers, so it is not an EndpointSource
PROBE_COVERAGE_SOURCE = "probe"

COVERAGE_SOURCE_LABELS: dict[str, str] = {
    **SOURCE_LABELS,
    PROBE_COVERAGE_SOURCE: "Verification",
}


def coerce_source(value: str | None) -> str:
    key = (value or "").strip().lower()
    return key if key in SOURCE_LABELS else EndpointSource.OTHER.value


def source_rank(value: str | None) -> int:
    return SOURCE_RANK.get(coerce_source(value), 0)


class EndpointClass(StrEnum):
    PAGE = "page"
    API = "api"
    SCRIPT = "script"
    STYLE = "style"
    DOCUMENT = "document"
    IMAGE = "image"
    MEDIA = "media"
    DATA = "data"
    ARCHIVE_FILE = "archive_file"
    OTHER = "other"


ENDPOINT_CLASSES: tuple[str, ...] = tuple(c.value for c in EndpointClass)

CLASS_LABELS: dict[str, str] = {
    EndpointClass.PAGE.value: "Pages",
    EndpointClass.API.value: "API",
    EndpointClass.SCRIPT.value: "Scripts",
    EndpointClass.STYLE.value: "Styles",
    EndpointClass.DOCUMENT.value: "Documents",
    EndpointClass.IMAGE.value: "Images",
    EndpointClass.MEDIA.value: "Media",
    EndpointClass.DATA.value: "Data",
    EndpointClass.ARCHIVE_FILE.value: "Archives",
    EndpointClass.OTHER.value: "Other",
}

CLASS_HELP: dict[str, str] = {
    EndpointClass.PAGE.value: "A rendered page, or a path with no file extension.",
    EndpointClass.API.value: "An API route, by path shape or by content type.",
    EndpointClass.SCRIPT.value: "JavaScript, including bundles and source maps.",
    EndpointClass.STYLE.value: "Stylesheets.",
    EndpointClass.DOCUMENT.value: "Documents that often carry metadata or internal detail.",
    EndpointClass.IMAGE.value: "Images.",
    EndpointClass.MEDIA.value: "Audio and video.",
    EndpointClass.DATA.value: "Structured data served as a file.",
    EndpointClass.ARCHIVE_FILE.value: "Archives and compressed files.",
    EndpointClass.OTHER.value: "Anything else.",
}

# classes that are content rather than attack surface; used to rank probe priority down
STATIC_CLASSES: frozenset[str] = frozenset(
    {
        EndpointClass.STYLE.value,
        EndpointClass.IMAGE.value,
        EndpointClass.MEDIA.value,
    }
)

# font files classify as OTHER but are static content all the same
STATIC_EXTENSIONS: frozenset[str] = frozenset({"woff", "woff2", "ttf", "eot", "otf"})


def is_static(endpoint_class: str | None, extension: str | None) -> bool:
    return (
        endpoint_class in STATIC_CLASSES
        or (extension or "").lower() in STATIC_EXTENSIONS
    )


class FolderGlyph(StrEnum):
    FOLDER = "folder"
    ADMIN = "admin"
    SENSITIVE = "sensitive"
    API = "api"
    AUTH = "auth"


_API_DOMINANT = 0.5

_EXTENSION_CLASS: dict[str, str] = {
    "html": EndpointClass.PAGE.value,
    "htm": EndpointClass.PAGE.value,
    "xhtml": EndpointClass.PAGE.value,
    "php": EndpointClass.PAGE.value,
    "asp": EndpointClass.PAGE.value,
    "aspx": EndpointClass.PAGE.value,
    "jsp": EndpointClass.PAGE.value,
    "jspx": EndpointClass.PAGE.value,
    "do": EndpointClass.PAGE.value,
    "action": EndpointClass.PAGE.value,
    "cgi": EndpointClass.PAGE.value,
    "pl": EndpointClass.PAGE.value,
    "cfm": EndpointClass.PAGE.value,
    "js": EndpointClass.SCRIPT.value,
    "mjs": EndpointClass.SCRIPT.value,
    "cjs": EndpointClass.SCRIPT.value,
    "jsx": EndpointClass.SCRIPT.value,
    "ts": EndpointClass.SCRIPT.value,
    "tsx": EndpointClass.SCRIPT.value,
    "map": EndpointClass.SCRIPT.value,
    "css": EndpointClass.STYLE.value,
    "scss": EndpointClass.STYLE.value,
    "less": EndpointClass.STYLE.value,
    "json": EndpointClass.DATA.value,
    "xml": EndpointClass.DATA.value,
    "yaml": EndpointClass.DATA.value,
    "yml": EndpointClass.DATA.value,
    "csv": EndpointClass.DATA.value,
    "sql": EndpointClass.DATA.value,
    "txt": EndpointClass.DATA.value,
    "rss": EndpointClass.DATA.value,
    "atom": EndpointClass.DATA.value,
    "graphql": EndpointClass.API.value,
    "wsdl": EndpointClass.API.value,
    "pdf": EndpointClass.DOCUMENT.value,
    "doc": EndpointClass.DOCUMENT.value,
    "docx": EndpointClass.DOCUMENT.value,
    "xls": EndpointClass.DOCUMENT.value,
    "xlsx": EndpointClass.DOCUMENT.value,
    "ppt": EndpointClass.DOCUMENT.value,
    "pptx": EndpointClass.DOCUMENT.value,
    "odt": EndpointClass.DOCUMENT.value,
    "rtf": EndpointClass.DOCUMENT.value,
    "png": EndpointClass.IMAGE.value,
    "jpg": EndpointClass.IMAGE.value,
    "jpeg": EndpointClass.IMAGE.value,
    "gif": EndpointClass.IMAGE.value,
    "svg": EndpointClass.IMAGE.value,
    "webp": EndpointClass.IMAGE.value,
    "ico": EndpointClass.IMAGE.value,
    "bmp": EndpointClass.IMAGE.value,
    "avif": EndpointClass.IMAGE.value,
    "mp4": EndpointClass.MEDIA.value,
    "webm": EndpointClass.MEDIA.value,
    "mov": EndpointClass.MEDIA.value,
    "avi": EndpointClass.MEDIA.value,
    "mp3": EndpointClass.MEDIA.value,
    "wav": EndpointClass.MEDIA.value,
    "ogg": EndpointClass.MEDIA.value,
    "zip": EndpointClass.ARCHIVE_FILE.value,
    "tar": EndpointClass.ARCHIVE_FILE.value,
    "gz": EndpointClass.ARCHIVE_FILE.value,
    "tgz": EndpointClass.ARCHIVE_FILE.value,
    "bz2": EndpointClass.ARCHIVE_FILE.value,
    "7z": EndpointClass.ARCHIVE_FILE.value,
    "rar": EndpointClass.ARCHIVE_FILE.value,
    "jar": EndpointClass.ARCHIVE_FILE.value,
    "war": EndpointClass.ARCHIVE_FILE.value,
    "bak": EndpointClass.ARCHIVE_FILE.value,
    "old": EndpointClass.ARCHIVE_FILE.value,
    "woff": EndpointClass.OTHER.value,
    "woff2": EndpointClass.OTHER.value,
    "ttf": EndpointClass.OTHER.value,
    "eot": EndpointClass.OTHER.value,
}

_CONTENT_TYPE_CLASS: tuple[tuple[str, str], ...] = (
    ("application/json", EndpointClass.API.value),
    ("application/graphql", EndpointClass.API.value),
    ("application/xml", EndpointClass.DATA.value),
    ("text/xml", EndpointClass.DATA.value),
    ("text/html", EndpointClass.PAGE.value),
    ("javascript", EndpointClass.SCRIPT.value),
    ("text/css", EndpointClass.STYLE.value),
    ("image/", EndpointClass.IMAGE.value),
    ("video/", EndpointClass.MEDIA.value),
    ("audio/", EndpointClass.MEDIA.value),
    ("application/pdf", EndpointClass.DOCUMENT.value),
    ("text/csv", EndpointClass.DATA.value),
    ("text/plain", EndpointClass.DATA.value),
)

_API_PATH_RE = re.compile(
    r"(^|/)(api|apis|rest|graphql|graphiql|gql|rpc|jsonrpc|odata|v[0-9]{1,2})(/|$)",
    re.IGNORECASE,
)


class ParamInterest(StrEnum):
    IDOR = "idor"
    OPEN_REDIRECT = "open_redirect"
    SSRF = "ssrf"
    TRAVERSAL = "traversal"
    SQLI = "sqli"
    XSS = "xss"
    RCE = "rce"
    SSTI = "ssti"
    UPLOAD = "upload"
    DEBUG = "debug"


PARAM_INTEREST_LABELS: dict[str, str] = {
    ParamInterest.IDOR.value: "Object reference",
    ParamInterest.OPEN_REDIRECT.value: "Open redirect",
    ParamInterest.SSRF.value: "Server-side request",
    ParamInterest.TRAVERSAL.value: "Path traversal",
    ParamInterest.SQLI.value: "SQL injection",
    ParamInterest.XSS.value: "Cross-site scripting",
    ParamInterest.RCE.value: "Command execution",
    ParamInterest.SSTI.value: "Template injection",
    ParamInterest.UPLOAD.value: "File upload",
    ParamInterest.DEBUG.value: "Debug switch",
}

PARAM_INTEREST_HELP: dict[str, str] = {
    ParamInterest.IDOR.value: "Names an object directly. Worth testing for access control.",
    ParamInterest.OPEN_REDIRECT.value: "Carries a destination the application redirects to.",
    ParamInterest.SSRF.value: "Carries a location the server fetches server-side.",
    ParamInterest.TRAVERSAL.value: "Carries a file or path the server reads.",
    ParamInterest.SQLI.value: "Commonly reaches a query directly.",
    ParamInterest.XSS.value: "Commonly reflected into the page.",
    ParamInterest.RCE.value: "Names a command or process the server runs.",
    ParamInterest.SSTI.value: "Names a template the server renders.",
    ParamInterest.UPLOAD.value: "Carries a file name or upload target.",
    ParamInterest.DEBUG.value: "Switches on diagnostic behaviour.",
}

# curated, not exhaustive: a name that flags everything flags nothing
PARAM_INTEREST: dict[str, frozenset[str]] = {
    ParamInterest.IDOR.value: frozenset(
        {
            "id",
            "uid",
            "userid",
            "user_id",
            "account",
            "account_id",
            "customer",
            "customer_id",
            "order",
            "order_id",
            "invoice",
            "doc",
            "document_id",
            "profile",
            "group_id",
            "org",
            "org_id",
            "tenant",
            "record",
        }
    ),
    ParamInterest.OPEN_REDIRECT.value: frozenset(
        {
            "redirect",
            "redirect_uri",
            "redirect_url",
            "redir",
            "return",
            "return_url",
            "returnto",
            "returnurl",
            "next",
            "goto",
            "continue",
            "dest",
            "destination",
            "target",
            "forward",
            "callback_url",
        }
    ),
    ParamInterest.SSRF.value: frozenset(
        {
            "url",
            "uri",
            "link",
            "src",
            "source",
            "fetch",
            "load",
            "proxy",
            "endpoint",
            "host",
            "domain",
            "site",
            "feed",
            "webhook",
            "callback",
            "image_url",
            "remote",
            "upstream",
        }
    ),
    ParamInterest.TRAVERSAL.value: frozenset(
        {
            "file",
            "filename",
            "filepath",
            "path",
            "folder",
            "dir",
            "directory",
            "download",
            "read",
            "include",
            "inc",
            "doc",
            "page_file",
            "attachment",
            "log",
            "conf",
            "config_file",
        }
    ),
    ParamInterest.SQLI.value: frozenset(
        {
            "sort",
            "order_by",
            "orderby",
            "column",
            "field",
            "table",
            "where",
            "filter",
            "query",
            "select",
            "group_by",
            "having",
            "limit",
            "offset",
            "search_column",
        }
    ),
    ParamInterest.XSS.value: frozenset(
        {
            "q",
            "s",
            "search",
            "keyword",
            "keywords",
            "query",
            "term",
            "message",
            "comment",
            "title",
            "subject",
            "body",
            "text",
            "name",
            "description",
            "note",
            "feedback",
        }
    ),
    ParamInterest.RCE.value: frozenset(
        {
            "cmd",
            "command",
            "exec",
            "execute",
            "run",
            "shell",
            "ping",
            "host_cmd",
            "process",
            "daemon",
            "job",
            "task",
            "script",
            "code",
            "eval",
        }
    ),
    ParamInterest.SSTI.value: frozenset(
        {
            "template",
            "tpl",
            "tmpl",
            "theme",
            "layout",
            "view",
            "render",
            "partial",
            "preview",
            "format",
        }
    ),
    ParamInterest.UPLOAD.value: frozenset(
        {"upload", "uploadfile", "attachment", "avatar", "photo", "image_file", "media"}
    ),
    ParamInterest.DEBUG.value: frozenset(
        {
            "debug",
            "test",
            "dev",
            "verbose",
            "trace",
            "profile_mode",
            "sql_debug",
            "admin_mode",
        }
    ),
}


def _build_param_lookup() -> dict[str, tuple[str, ...]]:
    out: dict[str, tuple[str, ...]] = {}
    for interest, names in PARAM_INTEREST.items():
        for name in names:
            out[name] = (*out.get(name, ()), interest)
    return out


_PARAM_LOOKUP: dict[str, tuple[str, ...]] = _build_param_lookup()


class PathInterest(StrEnum):
    VCS = "vcs"
    SECRETS = "secrets"
    BACKUP = "backup"
    ADMIN = "admin"
    API_DOC = "api_doc"
    DEBUG_ENDPOINT = "debug_endpoint"
    AUTH = "auth"
    INFRA = "infra"


PATH_INTEREST_LABELS: dict[str, str] = {
    PathInterest.VCS.value: "Version control",
    PathInterest.SECRETS.value: "Credential file",
    PathInterest.BACKUP.value: "Backup or temporary file",
    PathInterest.ADMIN.value: "Administrative interface",
    PathInterest.API_DOC.value: "API documentation",
    PathInterest.DEBUG_ENDPOINT.value: "Diagnostic endpoint",
    PathInterest.AUTH.value: "Authentication",
    PathInterest.INFRA.value: "Infrastructure service",
}

PATH_INTEREST_HELP: dict[str, str] = {
    PathInterest.VCS.value: "A version control directory served over HTTP exposes source and history.",
    PathInterest.SECRETS.value: "A file that conventionally holds credentials or keys.",
    PathInterest.BACKUP.value: "An editor or backup artefact left in the web root.",
    PathInterest.ADMIN.value: "An administrative interface reachable from the internet.",
    PathInterest.API_DOC.value: "A machine-readable description of the API surface.",
    PathInterest.DEBUG_ENDPOINT.value: "A diagnostic route that usually should not be public.",
    PathInterest.AUTH.value: "An authentication boundary.",
    PathInterest.INFRA.value: "A management or infrastructure service mounted on the web root.",
}

# matched as path substrings, lowercased; curated for signal
PATH_INTEREST: dict[str, tuple[str, ...]] = {
    PathInterest.VCS.value: ("/.git/", "/.git", "/.svn/", "/.hg/", "/.bzr/"),
    PathInterest.SECRETS.value: (
        "/.env",
        "/.aws/",
        "/.ssh/",
        "/.npmrc",
        "/.dockercfg",
        "/.docker/config",
        "/credentials",
        "/secrets",
        "/id_rsa",
        "/.htpasswd",
        "/web.config",
    ),
    PathInterest.BACKUP.value: (
        ".bak",
        ".old",
        ".orig",
        ".save",
        ".swp",
        ".swo",
        ".tmp",
        "~",
        "/backup/",
        "/backups/",
        ".sql",
        ".dump",
    ),
    PathInterest.ADMIN.value: (
        "/admin",
        "/administrator",
        "/wp-admin",
        "/manager/",
        "/console",
        "/cpanel",
        "/phpmyadmin",
        "/adminer",
        "/dashboard",
    ),
    PathInterest.API_DOC.value: (
        "/swagger",
        "/openapi",
        "/api-docs",
        "/apidocs",
        "/v2/api-docs",
        "/redoc",
        "/graphiql",
        "/graphql",
        "/.well-known/openapi",
    ),
    PathInterest.DEBUG_ENDPOINT.value: (
        "/actuator",
        "/debug",
        "/phpinfo",
        "/server-status",
        "/server-info",
        "/trace",
        "/heapdump",
        "/threaddump",
        "/metrics",
        "/prometheus",
        "/_profiler",
        "/telescope",
        "/__debug__",
    ),
    PathInterest.AUTH.value: (
        "/login",
        "/signin",
        "/sign-in",
        "/oauth",
        "/sso",
        "/saml",
        "/auth/",
        "/logout",
        "/register",
        "/password/reset",
    ),
    PathInterest.INFRA.value: (
        "/jenkins",
        "/jmx-console",
        "/solr",
        "/elasticsearch",
        "/kibana",
        "/grafana",
        "/rabbitmq",
        "/nagios",
        "/zabbix",
        "/.well-known/",
    ),
}

INTEREST_LABELS: dict[str, str] = {**PARAM_INTEREST_LABELS, **PATH_INTEREST_LABELS}
INTEREST_HELP: dict[str, str] = {**PARAM_INTEREST_HELP, **PATH_INTEREST_HELP}
INTEREST_KEYS: tuple[str, ...] = tuple(INTEREST_LABELS)

# an exposed file is a finding whatever serves it; an admin path is not when it is a logo
SENSITIVE_INTERESTS: frozenset[str] = frozenset(
    {PathInterest.VCS.value, PathInterest.SECRETS.value, PathInterest.BACKUP.value}
)
ADMIN_INTERESTS: frozenset[str] = frozenset(
    {
        PathInterest.ADMIN.value,
        PathInterest.DEBUG_ENDPOINT.value,
        PathInterest.INFRA.value,
    }
)

_DEFAULT_PORTS: dict[str, int] = {"http": 80, "https": 443}
_EXT_RE = re.compile(r"^[A-Za-z0-9]{1,10}$")
_HOST_RE = re.compile(r"^[a-z0-9._\-]+$|^[0-9a-f:.]+$")


@dataclass(frozen=True)
class ParsedUrl:
    url: str
    scheme: str
    host: str
    port: int
    path: str
    dir_path: str
    filename: str | None
    extension: str | None
    depth: int
    params: tuple[str, ...]
    param_values: dict[str, str]
    signature: str


def _collapse_dots(path: str) -> str:
    out: list[str] = []
    for segment in path.split("/"):
        if segment == ".":
            continue
        if segment == "..":
            if out:
                out.pop()
            continue
        out.append(segment)
    return "/".join(out)


def normalize_path(raw: str) -> str:
    path = raw or "/"
    if not path.startswith("/"):
        path = "/" + path
    path = re.sub(r"/{2,}", "/", path)
    trailing = path.endswith("/")
    path = _collapse_dots(path)
    if not path.startswith("/"):
        path = "/" + path
    if trailing and not path.endswith("/"):
        path += "/"
    if not path:
        path = "/"
    return path[:MAX_PATH_LENGTH]


def split_path(path: str) -> tuple[str, str | None, str | None, int]:
    """Directory, filename, extension and depth for a normalized path."""
    if path.endswith("/"):
        dir_path, filename = path, None
    else:
        cut = path.rfind("/")
        dir_path, filename = path[: cut + 1], path[cut + 1 :] or None
        # a path is capped, a single segment inside it is not — the column is
        if filename:
            filename = filename[:MAX_FILENAME_LENGTH]
    extension = None
    if filename and "." in filename:
        candidate = filename.rsplit(".", 1)[1]
        if _EXT_RE.match(candidate):
            extension = candidate.lower()
    depth = min(len([s for s in dir_path.split("/") if s]), MAX_DEPTH)
    return dir_path, filename, extension, depth


def parse_url(raw: str, *, default_scheme: str = "https") -> ParsedUrl | None:
    value = (raw or "").strip()
    if not value or len(value) > MAX_URL_LENGTH:
        return None
    if "://" not in value:
        value = f"{default_scheme}://{value}"
    try:
        parts = urlsplit(value)
    except ValueError:
        return None
    scheme = (parts.scheme or default_scheme).lower()
    if scheme not in _DEFAULT_PORTS:
        return None
    host = (parts.hostname or "").lower().strip(".")
    if not host or len(host) > MAX_HOST_LENGTH or not _HOST_RE.match(host):
        return None
    try:
        port = parts.port or _DEFAULT_PORTS[scheme]
    except ValueError:
        return None
    path = normalize_path(parts.path)
    dir_path, filename, extension, depth = split_path(path)

    values: dict[str, str] = {}
    for name, value_ in parse_qsl(parts.query, keep_blank_values=True):
        if name and name not in values:
            values[name] = value_[:200]
        if len(values) >= MAX_PARAMS:
            break
    params = tuple(sorted(values))

    literal = f"[{host}]" if ":" in host else host
    authority = literal if port == _DEFAULT_PORTS[scheme] else f"{literal}:{port}"
    query = "&".join(f"{n}={values[n]}" for n in params)
    url = f"{scheme}://{authority}{path}" + (f"?{query}" if query else "")
    return ParsedUrl(
        url=url[:MAX_URL_LENGTH],
        scheme=scheme,
        host=host,
        port=port,
        path=path,
        dir_path=dir_path,
        filename=filename,
        extension=extension,
        depth=depth,
        params=params,
        param_values=values,
        signature=signature_for(scheme, host, port, path, params),
    )


def signature_for(
    scheme: str, host: str, port: int, path: str, params: tuple[str, ...] | list[str]
) -> str:
    """Structural identity: values vary run to run, the shape does not."""
    key = f"{scheme}://{host}:{port}|{path}|{','.join(sorted(params))}"
    return hashlib.sha256(key.encode("utf-8", "replace")).hexdigest()


def classify(path: str, extension: str | None, content_type: str | None = None) -> str:
    if extension:
        mapped = _EXTENSION_CLASS.get(extension)
        if mapped and mapped != EndpointClass.PAGE.value:
            return mapped
    if content_type:
        head = content_type.split(";", 1)[0].strip().lower()
        for needle, klass in _CONTENT_TYPE_CLASS:
            if needle in head:
                if klass == EndpointClass.PAGE.value and _API_PATH_RE.search(path):
                    return EndpointClass.API.value
                return klass
    if _API_PATH_RE.search(path):
        return EndpointClass.API.value
    if extension:
        return _EXTENSION_CLASS.get(extension, EndpointClass.OTHER.value)
    return EndpointClass.PAGE.value


def param_interests(params: tuple[str, ...] | list[str] | None) -> list[str]:
    found: set[str] = set()
    for name in params or ():
        found.update(_PARAM_LOOKUP.get(name.strip().lower(), ()))
    return sorted(found)


def _path_has(lowered: str, needle: str) -> bool:
    # an editor backup ends in ~; a ~ inside a bundle name is just a hash separator
    if needle == "~":
        return lowered.endswith("~") or "~/" in lowered
    return needle in lowered


def path_interests(path: str) -> list[str]:
    lowered = (path or "").lower()
    return sorted(
        key
        for key, needles in PATH_INTEREST.items()
        if any(_path_has(lowered, needle) for needle in needles)
    )


def interests_for(
    path: str,
    params: tuple[str, ...] | list[str] | None,
    *,
    endpoint_class: str | None = None,
    extension: str | None = None,
) -> list[str]:
    by_path = path_interests(path)
    if is_static(endpoint_class, extension):
        by_path = [key for key in by_path if key in SENSITIVE_INTERESTS]
    return sorted({*by_path, *param_interests(params)})


def folder_glyph(interest: set[str] | frozenset[str], api: int, total: int) -> str:
    if interest & SENSITIVE_INTERESTS:
        return FolderGlyph.SENSITIVE.value
    if interest & ADMIN_INTERESTS:
        return FolderGlyph.ADMIN.value
    if total and api / total >= _API_DOMINANT:
        return FolderGlyph.API.value
    if PathInterest.AUTH.value in interest:
        return FolderGlyph.AUTH.value
    return FolderGlyph.FOLDER.value
