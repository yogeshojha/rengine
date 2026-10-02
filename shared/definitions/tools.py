import shlex

from pydantic import BaseModel

MAX_TOOL_OPTION_LEN = 1000


def parse_tool_args(raw: str) -> list[str]:
    """shlex-split custom tool args for execution."""
    if not raw:
        return []
    try:
        return shlex.split(raw)
    except ValueError:
        return []


class ToolSpec(BaseModel):
    name: str
    label: str
    phase: str
    example: str


SCAN_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="subfinder",
        label="Subfinder",
        phase="Subdomain Discovery",
        example="-all -recursive -timeout 30",
    ),
    ToolSpec(
        name="amass",
        label="Amass",
        phase="Subdomain Discovery",
        example="-active",
    ),
    ToolSpec(
        name="github-subdomains",
        label="GitHub Subdomains",
        phase="Subdomain Discovery",
        example="-e",
    ),
    ToolSpec(
        name="assetfinder",
        label="Assetfinder",
        phase="Subdomain Discovery",
        example="--subs-only",
    ),
    ToolSpec(
        name="tlsx",
        label="TLSX",
        phase="TLS / Certificates",
        example="-cn -san",
    ),
    ToolSpec(
        name="katana",
        label="Katana",
        phase="URL Discovery",
        example="-jc -kf all -aff",
    ),
    ToolSpec(
        name="urlfinder",
        label="URLFinder",
        phase="URL Discovery",
        example="-all",
    ),
    ToolSpec(
        name="dnsx",
        label="DNSX",
        phase="DNS Resolution",
        example="-rcode noerror",
    ),
    ToolSpec(
        name="alterx",
        label="Alterx",
        phase="Subdomain Discovery",
        example="-p '{{sub}}-{{word}}.{{suffix}}'",
    ),
    ToolSpec(
        name="naabu",
        label="Naabu",
        phase="Port Scan",
        example="-scan-all-ips -sn",
    ),
    ToolSpec(
        name="httpx",
        label="HTTPX",
        phase="HTTP Probe",
        example="-favicon -jarm",
    ),
    ToolSpec(
        name="nuclei",
        label="Nuclei",
        phase="Vulnerability Scan",
        example="-etags intrusive -exclude-severity info",
    ),
    ToolSpec(
        name="dalfox",
        label="Dalfox",
        phase="Fuzzing",
        example="--skip-ast-analysis",
    ),
    ToolSpec(
        name="ffuf",
        label="ffuf",
        phase="URL Discovery",
        example="-mc 200,204,301,302",
    ),
    ToolSpec(
        name="wafw00f",
        label="wafw00f",
        phase="WAF Detection",
        example="-a",
    ),
    ToolSpec(
        name="cdncheck",
        label="cdncheck",
        phase="CDN Attribution",
        example="-resp",
    ),
    ToolSpec(
        name="julius",
        label="julius",
        phase="AI Detection",
        example="--base-paths /api,/proxy",
    ),
)

TOOL_NAMES: frozenset[str] = frozenset(t.name for t in SCAN_TOOLS)

# flags refused in tool args, both spellings, without dashes
DENIED_FLAGS: dict[str, frozenset[str]] = {
    "nuclei": frozenset(
        {
            "ev",
            "env-vars",
            "code",
            "dut",
            "disable-unsigned-templates",
            "lfa",
            "allow-local-file-access",
            "turl",
            "template-url",
            "wurl",
            "workflow-url",
            "sf",
            "secret-file",
            "config",
            "tp",
            "profile",
            "rc",
            "report-config",
            "rdb",
            "report-db",
            "o",
            "output",
            "srd",
            "store-resp-dir",
            "elog",
            "error-log",
            "tlog",
            "trace-log",
            "me",
            "markdown-export",
            "se",
            "sarif-export",
            "je",
            "json-export",
            "jle",
            "jsonl-export",
            "pe",
            "pdf-export",
            "dtr",
            "dast-report",
            "dts",
            "dast-server",
            "resume",
            "project-path",
            "profile-mem",
            "ud",
            "update-template-dir",
            "reset",
            "auth",
            "pd",
            "dashboard",
            "pdu",
            "dashboard-upload",
            "cup",
            "cloud-upload",
            "tid",
            "team-id",
            "ho",
            "headless-options",
            "cdpe",
            "cdp-endpoint",
        }
    ),
    "httpx": frozenset(
        {
            "config",
            "sf",
            "secret-file",
            "o",
            "output",
            "oa",
            "output-all",
            "srd",
            "store-response-dir",
            "fepp",
            "filter-error-page-path",
            "rdbc",
            "result-db-config",
            "profile-mem",
            "auth",
            "ac",
            "auth-config",
            "pd",
            "dashboard",
            "pdu",
            "dashboard-upload",
            "tid",
            "team-id",
            "aid",
            "asset-id",
            "ho",
            "headless-options",
        }
    ),
    "katana": frozenset(
        {
            "config",
            "fc",
            "form-config",
            "flc",
            "field-config",
            "o",
            "output",
            "srd",
            "store-response-dir",
            "sfd",
            "store-field-dir",
            "elog",
            "error-log",
            "cdd",
            "chrome-data-dir",
            "scp",
            "system-chrome-path",
            "ho",
            "headless-options",
            "cwu",
            "chrome-ws-url",
        }
    ),
    "naabu": frozenset({"config", "o", "output", "nmap", "nmap-cli"}),
    "ffuf": frozenset(
        {
            "config",
            "o",
            "od",
            "debug-log",
            "audit-log",
            "input-cmd",
            "input-shell",
            "request",
        }
    ),
    "dnsx": frozenset({"o", "output", "ot", "output-template", "auth"}),
    "tlsx": frozenset(
        {
            "config",
            "o",
            "output",
            "ob",
            "openssl-binary",
            "auth",
            "pd",
            "dashboard",
            "pdu",
            "dashboard-upload",
            "tid",
            "team-id",
            "aid",
            "asset-id",
        }
    ),
    "subfinder": frozenset(
        {
            "config",
            "pc",
            "provider-config",
            "o",
            "output",
            "oD",
            "output-dir",
        }
    ),
    "urlfinder": frozenset(
        {
            "config",
            "pc",
            "provider-config",
            "o",
            "output",
            "od",
            "output-dir",
        }
    ),
    "alterx": frozenset({"config", "ac", "o", "output", "save-rules"}),
    "cdncheck": frozenset({"o", "output"}),
    "amass": frozenset({"config", "dir", "log", "o", "oA", "scripts"}),
    "github-subdomains": frozenset({"o"}),
    "assetfinder": frozenset(),
    "wafw00f": frozenset({"o", "output", "i", "input-file", "H", "headers"}),
    "dalfox": frozenset(
        {
            "config",
            "o",
            "output",
            "state-file",
            "cookie-from-raw",
            "custom-payload",
            "custom-blind-xss-payload",
        }
    ),
    "julius": frozenset({"f", "file", "p", "probes-dir"}),
}

CLUSTERED_SHORT_FLAGS: frozenset[str] = frozenset({"wafw00f", "dalfox", "julius"})
ABBREVIATED_LONG_FLAGS: frozenset[str] = frozenset({"wafw00f"})


def denied_flag(tool: str, tokens: list[str]) -> str | None:
    """First token naming a flag the tool refuses in tool args."""
    denied = DENIED_FLAGS.get(tool, frozenset())
    for token in tokens:
        flag = token.split("=", 1)[0]
        if not flag.startswith("-"):
            continue
        name = flag.lstrip("-")
        if name in denied:
            return flag
        if flag.startswith("--"):
            if tool in ABBREVIATED_LONG_FLAGS and any(
                len(d) > 1 and d.startswith(name) for d in denied if name
            ):
                return flag
        elif tool in CLUSTERED_SHORT_FLAGS and any(c in denied for c in token[1:]):
            return flag
    return None
