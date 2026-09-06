"""What a fresh install already knows. Editable where it should be, locked where it must be."""

from __future__ import annotations

from dataclasses import dataclass, field

from shared.definitions.interest import InterestKind, RuleMode


def _hosts(*tokens: str) -> str:
    """Anchored on label boundaries: `dr` must not match `drones`, the trap 2.x fell into."""
    body = "|".join(tokens)
    return f'host~"(^|[.-])({body})[0-9]{{0,2}}([.-]|$)"'


@dataclass(frozen=True)
class Preset:
    name: str
    kind: str
    description: str
    query: str = ""
    mode: str = RuleMode.QUERY.value
    keywords: tuple[str, ...] = ()
    keyword_fields: tuple[str, ...] = ()
    live_only: bool = False
    enabled: bool = True
    notify: bool = False
    weight: int | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)


PRESETS: tuple[Preset, ...] = (
    Preset(
        name="Your keywords",
        kind=InterestKind.OTHER.value,
        description="Anything you name, matched in the hostname or the page title.",
        mode=RuleMode.KEYWORD.value,
        keywords=("admin", "ftp", "cpanel", "dashboard"),
        keyword_fields=("host", "title"),
    ),
    Preset(
        name="Admin interfaces",
        kind=InterestKind.ADMIN_INTERFACE.value,
        description="An administrative surface answering without a login wall.",
        query=_hosts("admin", "portal", "console", "manage", "adminer")
        + " and is:live and not is:auth",
        notify=True,
    ),
    Preset(
        name="Hosting control panels",
        kind=InterestKind.ADMIN_INTERFACE.value,
        description="A hosting or server control panel on a public hostname.",
        query=_hosts("cpanel", "whm", "plesk", "directadmin", "webmin", "virtualmin")
        + " and is:live",
    ),
    Preset(
        name="Developer tooling exposed",
        kind=InterestKind.DEVELOPER_TOOLING.value,
        description="Build, source or observability tooling answering on the internet.",
        query="tech:[jenkins,gitlab,grafana,kibana,prometheus,sonarqube,jira,"
        "confluence,argocd,rancher,nexus,artifactory] and status:200",
        notify=True,
    ),
    Preset(
        name="Tooling hostnames",
        kind=InterestKind.DEVELOPER_TOOLING.value,
        description="A hostname that names internal tooling.",
        query=_hosts(
            "jenkins",
            "gitlab",
            "grafana",
            "kibana",
            "jira",
            "confluence",
            "vault",
            "consul",
            "nexus",
            "artifactory",
            "sonar",
        )
        + " and is:resolved",
    ),
    Preset(
        name="Remote access",
        kind=InterestKind.REMOTE_ACCESS.value,
        description="A VPN, gateway or remote desktop portal.",
        query=_hosts(
            "vpn",
            "remote",
            "rdp",
            "citrix",
            "gateway",
            "vdi",
            "anyconnect",
            "pulse",
        )
        + " and is:live",
    ),
    Preset(
        name="Business systems",
        kind=InterestKind.BUSINESS_SYSTEM.value,
        description="An ERP, finance or HR application reachable from outside.",
        query=_hosts(
            "sap",
            "erp",
            "oracle",
            "ebs",
            "payroll",
            "peoplesoft",
            "workday",
            "netsuite",
        )
        + " and is:resolved",
    ),
    Preset(
        name="Non-production exposed",
        kind=InterestKind.NON_PRODUCTION.value,
        description="A staging or test deployment served without authentication.",
        query=_hosts(
            "staging",
            "stg",
            "dev",
            "test",
            "uat",
            "qa",
            "sandbox",
            "preprod",
            "demo",
        )
        + " and is:live and not is:auth",
        notify=True,
    ),
    Preset(
        name="Retired deployments",
        kind=InterestKind.LEGACY.value,
        description="Named as old, retired or superseded, and still answering.",
        query=_hosts(
            "old", "legacy", "deprecated", "bak", "backup", "archive", "retired"
        )
        + " and is:live",
    ),
    Preset(
        name="Internal naming",
        kind=InterestKind.INTERNAL_NAMING.value,
        description="Internal or private naming on a publicly resolvable host.",
        query=_hosts("internal", "intranet", "corp", "priv", "private", "dmz", "lan")
        + " and is:resolved",
    ),
    Preset(
        name="Directory listings",
        kind=InterestKind.EXPOSED_CONTENT.value,
        description="A directory index served instead of a page.",
        query='body:"index of" and status:200',
    ),
    Preset(
        name="Key material in a response",
        kind=InterestKind.EXPOSED_CONTENT.value,
        description="Private key or cloud credential material in the response body.",
        query='body:"begin rsa private key" or body:"begin private key" '
        "or body:aws_secret_access_key",
        weight=60,
        notify=True,
    ),
    Preset(
        name="API documentation",
        kind=InterestKind.EXPOSED_CONTENT.value,
        description="A machine-readable description of the API surface, served publicly.",
        query="body:swagger or url:swagger or title:swagger or url:graphiql",
    ),
    Preset(
        name="Diagnostic output",
        kind=InterestKind.DIAGNOSTIC.value,
        description="Stack traces, debug pages or environment detail in the response.",
        query='body:traceback or body:"stack trace" or title:phpinfo or body:phpinfo',
    ),
    Preset(
        name="Database errors",
        kind=InterestKind.DIAGNOSTIC.value,
        description="Database error text returned to the client.",
        query='body:"sql syntax" or body:"odbc driver"',
    ),
    Preset(
        name="Dangling alias",
        kind=InterestKind.TAKEOVER_RISK.value,
        description="An alias record pointing at something that no longer answers.",
        query="cname:. and not is:web",
        notify=True,
    ),
    Preset(
        name="Third-party alias",
        kind=InterestKind.TAKEOVER_RISK.value,
        description="An alias pointing at third-party hosting with nothing serving it.",
        query="cname:[myshopify.com,github.io,herokuapp.com,azurewebsites.net,"
        "netlify.app,pantheonsite.io,wpengine.com,ghost.io] and not is:live",
        notify=True,
    ),
    Preset(
        name="Sensitive service open",
        kind=InterestKind.SENSITIVE_SERVICE.value,
        description="An administrative or database port is reachable on this host.",
        query="is:sensitive",
    ),
    Preset(
        name="Expired certificate",
        kind=InterestKind.CERTIFICATE_ANOMALY.value,
        description="Answering on a certificate that has expired.",
        query="cert:expired and is:live",
    ),
)

PRESET_BY_NAME: dict[str, Preset] = {p.name: p for p in PRESETS}


# what a shipped rule owns, versus what the user owns and an upgrade must never overwrite
SYNCED_FIELDS: tuple[str, ...] = ("description", "mode", "query", "kind")
USER_FIELDS: tuple[str, ...] = (
    "enabled",
    "notify",
    "keywords",
    "keyword_fields",
    "weight",
    "live_only",
)


def drift(rule, preset: Preset) -> dict:
    """Fields a shipped rule should adopt from the current preset."""
    changed = {}
    for name in SYNCED_FIELDS:
        wanted = getattr(preset, name)
        if getattr(rule, name) != wanted:
            changed[name] = wanted
    return changed
