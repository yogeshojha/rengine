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
    """katana -field-scope."""

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
    PROXY = "proxy"
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
    EndpointSource.PROXY.value: "Proxy",
    EndpointSource.IMPORT.value: "Imported",
    EndpointSource.OTHER.value: "Other",
}

SOURCE_HELP: dict[str, str] = {
    EndpointSource.SEED.value: "The web asset itself, as the HTTP probe recorded it.",
    EndpointSource.RESPONSE_MINING.value: "Extracted from a stored response body. No request was sent.",
    EndpointSource.CRAWL.value: "Reached by following links from a page on this host.",
    EndpointSource.ROBOTS.value: "Listed in robots.txt.",
    EndpointSource.SITEMAP.value: "Listed in the sitemap.",
    EndpointSource.ARCHIVE.value: "Recorded by a public archive.",
    EndpointSource.DEEP_ARCHIVE.value: "Recorded by a deep archive sweep.",
    EndpointSource.JS.value: "Extracted from a JavaScript bundle or its source map.",
    EndpointSource.FUZZ.value: "Guessed from a wordlist and answered.",
    EndpointSource.PARAM_MINING.value: "A parameter the endpoint accepts but did not advertise.",
    EndpointSource.VULN_SCAN.value: "A location a vulnerability scanner reported.",
    EndpointSource.PROXY.value: "Observed by a connected proxy.",
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
    EndpointSource.PROXY.value: SourceKind.DERIVED.value,
    EndpointSource.IMPORT.value: SourceKind.DERIVED.value,
    EndpointSource.OTHER.value: SourceKind.DERIVED.value,
}

SOURCE_RANK: dict[str, int] = {
    EndpointSource.OTHER.value: 0,
    EndpointSource.PROXY.value: 5,
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
    EndpointClass.DOCUMENT.value: "Documents.",
    EndpointClass.IMAGE.value: "Images.",
    EndpointClass.MEDIA.value: "Audio and video.",
    EndpointClass.DATA.value: "Structured data served as a file.",
    EndpointClass.ARCHIVE_FILE.value: "Archives and compressed files.",
    EndpointClass.OTHER.value: "Anything else.",
}

STATIC_CLASSES: frozenset[str] = frozenset(
    {
        EndpointClass.STYLE.value,
        EndpointClass.IMAGE.value,
        EndpointClass.MEDIA.value,
    }
)

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
    ParamInterest.IDOR.value: "Names an object directly.",
    ParamInterest.OPEN_REDIRECT.value: "Carries a destination the application redirects to.",
    ParamInterest.SSRF.value: "Carries a location the server fetches server-side.",
    ParamInterest.TRAVERSAL.value: "Carries a file or path the server reads.",
    ParamInterest.SQLI.value: "Reaches a database query.",
    ParamInterest.XSS.value: "Reflected into the page.",
    ParamInterest.RCE.value: "Names a command or process the server runs.",
    ParamInterest.SSTI.value: "Names a template the server renders.",
    ParamInterest.UPLOAD.value: "Carries a file name or upload target.",
    ParamInterest.DEBUG.value: "Switches on diagnostic behaviour.",
}

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

PARAM_INTEREST_ORDER: tuple[str, ...] = (
    ParamInterest.RCE.value,
    ParamInterest.SQLI.value,
    ParamInterest.SSRF.value,
    ParamInterest.TRAVERSAL.value,
    ParamInterest.OPEN_REDIRECT.value,
    ParamInterest.IDOR.value,
    ParamInterest.UPLOAD.value,
    ParamInterest.SSTI.value,
    ParamInterest.DEBUG.value,
    ParamInterest.XSS.value,
)

MAX_HOST_PARAMS = 60
MAX_HOST_CHIPS = 8


def param_interest(name: str) -> str | None:
    hits = _PARAM_LOOKUP.get(name.lower())
    if not hits:
        return None
    return min(hits, key=PARAM_INTEREST_ORDER.index)


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
    PathInterest.VCS.value: "A version control directory served over HTTP.",
    PathInterest.SECRETS.value: "A file that conventionally holds credentials or keys.",
    PathInterest.BACKUP.value: "A backup or editor file in the web root.",
    PathInterest.ADMIN.value: "An administrative interface reachable from the internet.",
    PathInterest.API_DOC.value: "A machine-readable description of the API surface.",
    PathInterest.DEBUG_ENDPOINT.value: "A diagnostic route.",
    PathInterest.AUTH.value: "An authentication boundary.",
    PathInterest.INFRA.value: "A management or infrastructure service mounted on the web root.",
}

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
        "/.well-known/openid-configuration",
        "/.well-known/oauth-authorization-server",
        "/.well-known/ai-plugin.json",
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
    ),
}

INTEREST_LABELS: dict[str, str] = {**PARAM_INTEREST_LABELS, **PATH_INTEREST_LABELS}
INTEREST_HELP: dict[str, str] = {**PARAM_INTEREST_HELP, **PATH_INTEREST_HELP}
INTEREST_KEYS: tuple[str, ...] = tuple(INTEREST_LABELS)

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

WHY_INTERESTS: tuple[str, ...] = (
    PathInterest.VCS.value,
    PathInterest.SECRETS.value,
    PathInterest.BACKUP.value,
    PathInterest.ADMIN.value,
    PathInterest.DEBUG_ENDPOINT.value,
    PathInterest.INFRA.value,
    PathInterest.API_DOC.value,
    PathInterest.AUTH.value,
    ParamInterest.RCE.value,
    ParamInterest.SQLI.value,
    ParamInterest.SSRF.value,
    ParamInterest.TRAVERSAL.value,
    ParamInterest.OPEN_REDIRECT.value,
    ParamInterest.IDOR.value,
    ParamInterest.UPLOAD.value,
    ParamInterest.SSTI.value,
    ParamInterest.DEBUG.value,
)

ROOT_NOISE_FILES: frozenset[str] = frozenset(
    {"", "robots.txt", "sitemap.xml", "sitemap_index.xml", "favicon.ico", "humans.txt"}
)
ROOT_NOISE_DIRS: tuple[str, ...] = ("/.well-known/",)

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
    family: str


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
        family=family_for(host, port, path, params),
    )


def signature_for(
    scheme: str, host: str, port: int, path: str, params: tuple[str, ...] | list[str]
) -> str:
    """Structural identity of an endpoint."""
    key = f"{scheme}://{host}:{port}|{path}|{','.join(sorted(params))}"
    return hashlib.sha256(key.encode("utf-8", "replace")).hexdigest()


# ---------- path shape ----------

SHAPE_PLACEHOLDER = "{id}"
_SHAPE_MIN_TOKEN = 12
_SHAPE_MIN_STEM = 10
_SHAPE_MIN_DIGITS = 3
_SHAPE_NUMERIC = re.compile(r"^\d+$")
_SHAPE_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)
_SHAPE_HEX = re.compile(r"^[0-9a-f]{16,}$", re.IGNORECASE)
_SHAPE_TOKEN = re.compile(r"^[A-Za-z0-9_-]{20,}$")
_SHAPE_MIXED = re.compile(r"^(?=.*\d)(?=.*[A-Za-z])[A-Za-z0-9]{8,}$")
_SHAPE_HASH_STEM = re.compile(r"^[a-z0-9]+$", re.IGNORECASE)
_SHAPE_NAMED_HASH = re.compile(r"^(.+)-([a-z0-9]{8,})$", re.IGNORECASE)


def _variable_segment(segment: str) -> bool:
    if not segment or "." in segment:
        return False
    if (
        _SHAPE_NUMERIC.match(segment)
        or _SHAPE_UUID.match(segment)
        or _SHAPE_HEX.match(segment)
    ):
        return True
    return len(segment) >= _SHAPE_MIN_TOKEN and bool(
        _SHAPE_TOKEN.match(segment) or _SHAPE_MIXED.match(segment)
    )


def _hashed_filename(segment: str) -> str | None:
    stem, dot, extension = segment.rpartition(".")
    if not dot or "." in stem:
        return None
    named = _SHAPE_NAMED_HASH.match(stem)
    if named and sum(c.isdigit() for c in named.group(2)) >= _SHAPE_MIN_DIGITS:
        return f"{named.group(1)}-{SHAPE_PLACEHOLDER}.{extension}"
    if (
        len(stem) >= _SHAPE_MIN_STEM
        and _SHAPE_HASH_STEM.match(stem)
        and sum(c.isdigit() for c in stem) >= _SHAPE_MIN_DIGITS
        and any(c.isalpha() for c in stem)
    ):
        return f"{SHAPE_PLACEHOLDER}.{extension}"
    return None


def shape_for(path: str) -> tuple[str, int]:
    """The path with identifier segments collapsed, and how many were collapsed."""
    if not path or path == "/":
        return path or "/", 0
    trailing = path.endswith("/")
    parts = [p for p in path.split("/") if p]
    replaced = 0
    out: list[str] = []
    last = len(parts) - 1
    for index, segment in enumerate(parts):
        if _variable_segment(segment):
            replaced += 1
            out.append(SHAPE_PLACEHOLDER)
            continue
        hashed = _hashed_filename(segment) if index == last else None
        if hashed is not None:
            replaced += 1
            out.append(hashed)
            continue
        out.append(segment)
    shaped = "/" + "/".join(out)
    if trailing and not shaped.endswith("/"):
        shaped += "/"
    return shaped[:MAX_PATH_LENGTH], replaced


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


# ---------- noise ----------


class NoiseRule(StrEnum):
    STATIC = "static"
    ARTIFACT = "artifact"
    PLATFORM = "platform"
    FAMILY = "family"
    LOCALE = "locale"
    SIBLINGS = "siblings"
    NOT_FOUND = "not_found"
    SAME_RESPONSE = "same_response"
    SAME_REDIRECT = "same_redirect"
    CATCH_ALL = "catch_all"
    SIMILAR_RESPONSE = "similar_response"
    ARCHIVE_ROT = "archive_rot"
    OFF_SCOPE = "off_scope"


URL_RULES: tuple[str, ...] = (
    NoiseRule.STATIC.value,
    NoiseRule.ARTIFACT.value,
    NoiseRule.PLATFORM.value,
    NoiseRule.FAMILY.value,
    NoiseRule.LOCALE.value,
    NoiseRule.SIBLINGS.value,
)
RESPONSE_RULES: tuple[str, ...] = (
    NoiseRule.NOT_FOUND.value,
    NoiseRule.SAME_RESPONSE.value,
    NoiseRule.SAME_REDIRECT.value,
    NoiseRule.CATCH_ALL.value,
    NoiseRule.SIMILAR_RESPONSE.value,
    NoiseRule.ARCHIVE_ROT.value,
    NoiseRule.OFF_SCOPE.value,
)

NOISE_RULE_LABELS: dict[str, str] = {
    NoiseRule.STATIC.value: "Static files",
    NoiseRule.ARTIFACT.value: "Crawler artifacts",
    NoiseRule.PLATFORM.value: "Platform noise",
    NoiseRule.FAMILY.value: "Past the family cap",
    NoiseRule.LOCALE.value: "Other languages",
    NoiseRule.SIBLINGS.value: "Past the sibling cap",
    NoiseRule.NOT_FOUND.value: "Not found",
    NoiseRule.SAME_RESPONSE.value: "Same response",
    NoiseRule.SAME_REDIRECT.value: "Same redirect",
    NoiseRule.CATCH_ALL.value: "Same as the site root",
    NoiseRule.SIMILAR_RESPONSE.value: "Similar response",
    NoiseRule.ARCHIVE_ROT.value: "Archive rot",
    NoiseRule.OFF_SCOPE.value: "Redirect out of scope",
}

NOISE_RULE_HELP: dict[str, str] = {
    NoiseRule.STATIC.value: "Images, fonts, media and stylesheets.",
    NoiseRule.ARTIFACT.value: "Template literals, quotes and JavaScript values read as URLs.",
    NoiseRule.PLATFORM.value: "Feeds, oEmbed, print views, comment replies and CDN paths.",
    NoiseRule.FAMILY.value: "URLs that differ from a kept one only by an identifier.",
    NoiseRule.LOCALE.value: "The same path under another language prefix.",
    NoiseRule.SIBLINGS.value: "Children of one folder past the cap, of one kind.",
    NoiseRule.NOT_FOUND.value: "The response matches what the host answers for a path that does not exist.",
    NoiseRule.SAME_RESPONSE.value: "Byte-identical to a kept response on the host.",
    NoiseRule.SAME_REDIRECT.value: "Redirects where a kept URL on the host already redirects.",
    NoiseRule.CATCH_ALL.value: "The site root's response served at another path.",
    NoiseRule.SIMILAR_RESPONSE.value: "Same status, title and size as ten or more kept responses.",
    NoiseRule.ARCHIVE_ROT.value: "Known only from archives and gone.",
    NoiseRule.OFF_SCOPE.value: "Redirects to a host outside the scan.",
}

NOT_FOUND_TOLERANCE = 0.02
SAME_RESPONSE_MIN = 3
SAME_REDIRECT_MIN = 5
SIMILAR_RESPONSE_MIN = 10
CANARY_LENGTH = 24

NOISE_STATIC_EXTENSIONS: tuple[str, ...] = (
    "png",
    "jpg",
    "jpeg",
    "gif",
    "svg",
    "webp",
    "avif",
    "bmp",
    "ico",
    "tif",
    "tiff",
    "css",
    "scss",
    "less",
    "map",
    "woff",
    "woff2",
    "ttf",
    "eot",
    "otf",
    "mp4",
    "webm",
    "mov",
    "avi",
    "mp3",
    "wav",
    "ogg",
    "m4a",
    "flac",
)

NOISE_IGNORED_PARAMS: tuple[str, ...] = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "fbclid",
    "gclid",
    "dclid",
    "msclkid",
    "yclid",
    "mc_cid",
    "mc_eid",
    "_ga",
    "_gl",
    "_hsenc",
    "_hsmi",
    "ref",
    "v",
    "ver",
    "version",
    "_",
    "cb",
    "cache",
    "nocache",
    "rand",
    "random",
    "t",
    "ts",
    "timestamp",
    "hash",
    "rev",
    "build",
    "itok",
    "cachebuster",
)
NOISE_IGNORED_PARAM_PREFIXES: tuple[str, ...] = ("utm_",)

NOISE_KEEP_PER_FAMILY = 3
NOISE_SIBLING_CAP = 12
MAX_NOISE_KEEP_PER_FAMILY = 100
MAX_NOISE_SIBLING_CAP = 1000

INDEX_FILES: frozenset[str] = frozenset(
    {
        "index.html",
        "index.htm",
        "index.php",
        "index.jsp",
        "index.asp",
        "index.aspx",
        "default.asp",
        "default.aspx",
        "default.htm",
        "default.html",
    }
)

LANG_PLACEHOLDER = "{lang}"
_LANG_RE = re.compile(r"^([a-z]{2})(?:[-_][a-z]{2,4}){0,2}$", re.IGNORECASE)
_LANG_PRIMARY: frozenset[str] = frozenset(
    [
        "aa",
        "ab",
        "af",
        "ak",
        "am",
        "ar",
        "av",
        "ay",
        "az",
        "ba",
        "bg",
        "bh",
        "bi",
        "bm",
        "bn",
        "bo",
        "br",
        "bs",
        "ca",
        "ce",
        "ch",
        "co",
        "cr",
        "cs",
        "cu",
        "cv",
        "cy",
        "da",
        "de",
        "dv",
        "dz",
        "ee",
        "el",
        "en",
        "eo",
        "es",
        "et",
        "eu",
        "fa",
        "ff",
        "fi",
        "fj",
        "fo",
        "fr",
        "fy",
        "ga",
        "gd",
        "gl",
        "gn",
        "gu",
        "gv",
        "ha",
        "he",
        "hi",
        "ho",
        "hr",
        "ht",
        "hu",
        "hy",
        "hz",
        "ia",
        "ie",
        "ig",
        "ii",
        "ik",
        "it",
        "iu",
        "ja",
        "jv",
        "ka",
        "kg",
        "ki",
        "kj",
        "kk",
        "kl",
        "km",
        "kn",
        "ko",
        "kr",
        "ks",
        "ku",
        "kv",
        "kw",
        "ky",
        "la",
        "lb",
        "lg",
        "li",
        "ln",
        "lo",
        "lt",
        "lu",
        "lv",
        "mg",
        "mh",
        "mi",
        "mk",
        "ml",
        "mn",
        "mr",
        "ms",
        "mt",
        "na",
        "nb",
        "nd",
        "ne",
        "ng",
        "nl",
        "nn",
        "nr",
        "nv",
        "ny",
        "oc",
        "oj",
        "om",
        "os",
        "pa",
        "pi",
        "pl",
        "ps",
        "pt",
        "qu",
        "rm",
        "rn",
        "ro",
        "ru",
        "rw",
        "sa",
        "sc",
        "sd",
        "se",
        "sg",
        "si",
        "sk",
        "sl",
        "sm",
        "sn",
        "sq",
        "sr",
        "ss",
        "st",
        "su",
        "sv",
        "sw",
        "ta",
        "te",
        "tg",
        "th",
        "ti",
        "tk",
        "tl",
        "tn",
        "tr",
        "ts",
        "tt",
        "tw",
        "ty",
        "ug",
        "uk",
        "ur",
        "uz",
        "ve",
        "vi",
        "vo",
        "wa",
        "wo",
        "xh",
        "yi",
        "yo",
        "za",
        "zh",
        "zu",
    ]
)
_LANG_NOT: frozenset[str] = frozenset(
    {"my", "me", "us", "go", "to", "in", "on", "at", "by", "or", "an", "as", "be", "do", "if", "is", "so", "no", "io", "ai", "tv", "id"}
)  # fmt: skip

_TOKEN_PARAM_RE = re.compile(r"^(?=.*[a-z])[a-z0-9]{8,}$")
_TOKEN_PARAM_MIN_DIGITS = 3
_SESSION_PATH_RE = re.compile(r";[A-Za-z_]+=[^/?#]*", re.IGNORECASE)
_ARTIFACT_RE = re.compile(
    r"\{\{|\}\}|\$\{|%7B%7B|%7D%7D|%24%7B|[<>\"`\\]|%3C|%3E|%22|%5C|%60",
    re.IGNORECASE,
)
_ARTIFACT_SEGMENTS: frozenset[str] = frozenset(
    {
        "undefined",
        "null",
        "nan",
        "[object object]",
        "%5bobject%20object%5d",
        "true",
        "false",
    }
)
_PLATFORM_PATH_RE = re.compile(
    r"(^|/)(feed|rss|atom|comments/feed|wp-json/oembed|cdn-cgi|trackback)(/|$)",
    re.IGNORECASE,
)
_PLATFORM_PARAMS: frozenset[str] = frozenset(
    {"replytocom", "share", "print", "printable", "tmpl", "format", "output", "amp"}
)
_PLATFORM_PARAM_VALUES: dict[str, frozenset[str]] = {
    "tmpl": frozenset({"component", "print"}),
    "format": frozenset({"feed", "rss", "atom", "print", "pdf", "amp"}),
    "output": frozenset({"rss", "atom", "amp"}),
}


def is_lang_segment(segment: str) -> bool:
    match = _LANG_RE.match(segment)
    if match is None:
        return False
    primary = match.group(1).lower()
    return primary in _LANG_PRIMARY and primary not in _LANG_NOT


def is_ignored_param(name: str, ignored: frozenset[str] | None = None) -> bool:
    lowered = name.strip().lower()
    names = ignored if ignored is not None else frozenset(NOISE_IGNORED_PARAMS)
    if lowered in names or lowered.startswith(NOISE_IGNORED_PARAM_PREFIXES):
        return True
    if (
        _SHAPE_NUMERIC.match(lowered)
        or _SHAPE_UUID.match(lowered)
        or _SHAPE_HEX.match(lowered)
    ):
        return True
    return bool(_TOKEN_PARAM_RE.match(lowered)) and (
        sum(c.isdigit() for c in lowered) >= _TOKEN_PARAM_MIN_DIGITS
    )


def is_artifact(path: str) -> bool:
    if _ARTIFACT_RE.search(path):
        return True
    return any(s.lower() in _ARTIFACT_SEGMENTS for s in path.split("/") if s)


def is_platform_noise(
    path: str, params: tuple[str, ...], values: dict[str, str]
) -> bool:
    if _PLATFORM_PATH_RE.search(path):
        return True
    for name in params:
        lowered = name.lower()
        if lowered not in _PLATFORM_PARAMS:
            continue
        allowed = _PLATFORM_PARAM_VALUES.get(lowered)
        if allowed is None or (values.get(name) or "").lower() in allowed:
            return True
    return False


def strip_session_path(path: str) -> str:
    return _SESSION_PATH_RE.sub("", path)


def fold_index_file(path: str) -> str:
    cut = path.rfind("/")
    if cut >= 0 and path[cut + 1 :].lower() in INDEX_FILES:
        return path[: cut + 1]
    return path


def lang_of(path: str) -> str | None:
    """The leading language segment, or None."""
    first = path.split("/", 2)[1] if path.startswith("/") else ""
    return first.lower() if first and is_lang_segment(first) else None


def family_shape(path: str) -> str:
    """The shape with a leading language segment folded."""
    shaped, _ = shape_for(path)
    lang = lang_of(path)
    if lang is None:
        return shaped
    rest = shaped.split("/", 2)[2:]
    return "/" + LANG_PLACEHOLDER + ("/" + rest[0] if rest else "")


def family_for(
    host: str, port: int, path: str, params: tuple[str, ...] | list[str]
) -> str:
    """Structural family of an endpoint: scheme-agnostic, identifiers and language folded."""
    names = sorted(n for n in params if not is_ignored_param(n))
    key = f"{host}:{port}|{family_shape(path)}|{','.join(names)}"
    return hashlib.sha256(key.encode("utf-8", "replace")).hexdigest()


def sibling_key(path: str, extension: str | None) -> tuple[str, str] | None:
    """The folder and kind a leaf competes in, or None for a folded or root path."""
    if path == "/" or shape_for(path)[1]:
        return None
    trimmed = path[:-1] if path.endswith("/") else path
    cut = trimmed.rfind("/")
    if cut < 0:
        return None
    parent = trimmed[: cut + 1]
    kind = "dir" if path.endswith("/") else (extension or "")
    return parent, kind
