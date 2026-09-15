"""Secrets read out of stored HTTP responses. Nothing is sent to verify one."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from shared.definitions.constants import HTTPX_RESPONSE_CAP
from shared.definitions.interest import TONE_INFO, TONE_NEUTRAL, TONE_WARNING

MAX_VALUE_LENGTH = 8192
MAX_SUBJECT_LENGTH = 500
MAX_CONTEXT_LENGTH = 1200
CONTEXT_RADIUS = 300
MAX_SIGHTINGS_PER_SECRET = 100
MAX_SIGHTINGS_SHOWN = 100
MIN_ENTROPY_LENGTH = 20
MIN_ENTROPY_BITS = 3.0
WRITE_BATCH = 200
BACKFILL_SCANS_PER_TICK = 5
BODY_CAP_BYTES = HTTPX_RESPONSE_CAP


class SecretGroup(StrEnum):
    CLOUD = "cloud"
    CODE = "code"
    PAYMENTS = "payments"
    MESSAGING = "messaging"
    AI = "ai"
    AUTH = "auth"
    DATA = "data"
    PLATFORM = "platform"
    CONTACT = "contact"


GROUP_ORDER: tuple[str, ...] = tuple(g.value for g in SecretGroup)

GROUP_LABELS: dict[str, str] = {
    SecretGroup.CLOUD.value: "Cloud",
    SecretGroup.CODE.value: "Source control and packages",
    SecretGroup.PAYMENTS.value: "Payments",
    SecretGroup.MESSAGING.value: "Messaging",
    SecretGroup.AI.value: "AI providers",
    SecretGroup.AUTH.value: "Authentication",
    SecretGroup.DATA.value: "Data stores",
    SecretGroup.PLATFORM.value: "Platform and tooling",
    SecretGroup.CONTACT.value: "Contacts",
}


class SecretState(StrEnum):
    EXPOSED = "exposed"
    PUBLIC = "public"
    EXPIRED = "expired"


STATE_ORDER: tuple[str, ...] = tuple(s.value for s in SecretState)

STATE_LABELS: dict[str, str] = {
    SecretState.EXPOSED.value: "Exposed",
    SecretState.PUBLIC.value: "Public",
    SecretState.EXPIRED.value: "Expired",
}

STATE_TONES: dict[str, str] = {
    SecretState.EXPOSED.value: TONE_WARNING,
    SecretState.PUBLIC.value: TONE_NEUTRAL,
    SecretState.EXPIRED.value: TONE_INFO,
}


class SecretSource(StrEnum):
    BODY = "body"
    HEADER = "header"


SOURCE_LABELS: dict[str, str] = {
    SecretSource.BODY.value: "Response body",
    SecretSource.HEADER.value: "Response headers",
}


class MinerSource(StrEnum):
    STORED_RESPONSES = "stored_responses"


MINER_SOURCE_LABELS: dict[str, str] = {
    MinerSource.STORED_RESPONSES.value: "Stored responses",
}


class DropReason(StrEnum):
    PLACEHOLDER = "placeholder"
    LOW_ENTROPY = "low_entropy"
    OVERLAP = "overlap"
    FILE_NAME = "file_name"
    EXAMPLE_DOMAIN = "example_domain"
    HEX_LOCAL_PART = "hex_local_part"
    UNDECODABLE = "undecodable"
    TEMPLATE = "template"
    TOO_LONG = "too_long"


DROP_REASON_LABELS: dict[str, str] = {
    DropReason.PLACEHOLDER.value: "Placeholder value",
    DropReason.LOW_ENTROPY.value: "Low entropy",
    DropReason.OVERLAP.value: "Inside a longer match",
    DropReason.FILE_NAME.value: "File name, not an address",
    DropReason.EXAMPLE_DOMAIN.value: "Example domain",
    DropReason.HEX_LOCAL_PART.value: "Hex local part",
    DropReason.UNDECODABLE.value: "Token did not decode",
    DropReason.TEMPLATE.value: "Template expression",
    DropReason.TOO_LONG.value: "Over the length cap",
}


class Validator(StrEnum):
    NONE = "none"
    TOKEN = "token"  # noqa: S105
    JWT = "jwt"
    CREDENTIAL_URL = "credential_url"
    EMAIL = "email"
    PRIVATE_KEY = "private_key"


@dataclass(frozen=True)
class DetectorSpec:
    key: str
    label: str
    vendor: str
    group: str
    pattern: str
    anchors: tuple[str, ...]
    public: bool = False
    validator: str = Validator.TOKEN.value

    @property
    def query(self) -> str:
        return f"secret:{self.key}"


_URL_USER = r"[^\s/:@\"'<>`\\]{1,64}"
_URL_PASS = r"[^\s/@\"'<>`\\]{1,128}"  # noqa: S105
_URL_HOST = r"[A-Za-z0-9][A-Za-z0-9.\-]{0,253}(?::[0-9]{1,5})?"
_PEM_KIND = r"(?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY(?: BLOCK)?"

DETECTORS: tuple[DetectorSpec, ...] = (
    # ---------- cloud ----------
    DetectorSpec(
        "aws_access_key",
        "AWS access key",
        "Amazon Web Services",
        SecretGroup.CLOUD.value,
        r"\b((?:AKIA|ASIA)[0-9A-Z]{16})\b",
        ("AKIA", "ASIA"),
    ),
    DetectorSpec(
        "aws_secret_key",
        "AWS secret key",
        "Amazon Web Services",
        SecretGroup.CLOUD.value,
        r"(?i)aws[_\-\s]*secret[_\-\s]*(?:access[_\-\s]*)?key[\"'\s]*[:=]\s*[\"']?([A-Za-z0-9/+]{40})(?![A-Za-z0-9/+])",
        ("aws", "AWS", "Aws"),
    ),
    DetectorSpec(
        "google_api_key",
        "Google API key",
        "Google",
        SecretGroup.CLOUD.value,
        r"\b(AIza[0-9A-Za-z_\-]{35})\b",
        ("AIza",),
    ),
    DetectorSpec(
        "google_oauth_secret",
        "Google OAuth client secret",
        "Google",
        SecretGroup.CLOUD.value,
        r"\b(GOCSPX-[A-Za-z0-9_\-]{28})\b",
        ("GOCSPX-",),
    ),
    DetectorSpec(
        "google_oauth_client_id",
        "Google OAuth client id",
        "Google",
        SecretGroup.CLOUD.value,
        r"\b([0-9]{10,14}-[a-z0-9]{32}\.apps\.googleusercontent\.com)\b",
        (".apps.googleusercontent.com",),
        public=True,
        validator=Validator.NONE.value,
    ),
    DetectorSpec(
        "azure_storage_key",
        "Azure storage account key",
        "Microsoft Azure",
        SecretGroup.CLOUD.value,
        r"AccountKey=([A-Za-z0-9+/]{86}==)",
        ("AccountKey=",),
    ),
    DetectorSpec(
        "digitalocean_token",
        "DigitalOcean token",
        "DigitalOcean",
        SecretGroup.CLOUD.value,
        r"\b(do[po]_v1_[a-f0-9]{64})\b",
        ("dop_v1_", "doo_v1_"),
    ),
    # ---------- code ----------
    DetectorSpec(
        "github_token",
        "GitHub token",
        "GitHub",
        SecretGroup.CODE.value,
        r"\b(gh[pousr]_[A-Za-z0-9]{36})\b",
        ("ghp_", "gho_", "ghu_", "ghs_", "ghr_"),
    ),
    DetectorSpec(
        "github_fine_grained_token",
        "GitHub fine-grained token",
        "GitHub",
        SecretGroup.CODE.value,
        r"\b(github_pat_[A-Za-z0-9_]{82})\b",
        ("github_pat_",),
    ),
    DetectorSpec(
        "gitlab_token",
        "GitLab token",
        "GitLab",
        SecretGroup.CODE.value,
        r"\b(glpat-[A-Za-z0-9_\-]{20,})\b",
        ("glpat-",),
    ),
    DetectorSpec(
        "npm_token",
        "npm token",
        "npm",
        SecretGroup.CODE.value,
        r"\b(npm_[A-Za-z0-9]{36})\b",
        ("npm_",),
    ),
    DetectorSpec(
        "pypi_token",
        "PyPI token",
        "PyPI",
        SecretGroup.CODE.value,
        r"(pypi-AgEIcHlwaS5vcmc[A-Za-z0-9_\-]{50,})",
        ("pypi-AgEIcHlwaS5vcmc",),
    ),
    DetectorSpec(
        "huggingface_token",
        "Hugging Face token",
        "Hugging Face",
        SecretGroup.CODE.value,
        r"\b(hf_[A-Za-z0-9]{34})\b",
        ("hf_",),
    ),
    # ---------- payments ----------
    DetectorSpec(
        "stripe_secret_key",
        "Stripe secret key",
        "Stripe",
        SecretGroup.PAYMENTS.value,
        r"\b([sr]k_live_[0-9a-zA-Z]{24,99})\b",
        ("sk_live_", "rk_live_"),
    ),
    DetectorSpec(
        "stripe_publishable_key",
        "Stripe publishable key",
        "Stripe",
        SecretGroup.PAYMENTS.value,
        r"\b(pk_live_[0-9a-zA-Z]{24,99})\b",
        ("pk_live_",),
        public=True,
        validator=Validator.NONE.value,
    ),
    DetectorSpec(
        "square_access_token",
        "Square access token",
        "Square",
        SecretGroup.PAYMENTS.value,
        r"\b(sq0atp-[0-9A-Za-z_\-]{22})\b",
        ("sq0atp-",),
    ),
    DetectorSpec(
        "square_secret",
        "Square application secret",
        "Square",
        SecretGroup.PAYMENTS.value,
        r"\b(sq0csp-[0-9A-Za-z_\-]{43})\b",
        ("sq0csp-",),
    ),
    DetectorSpec(
        "shopify_token",
        "Shopify token",
        "Shopify",
        SecretGroup.PAYMENTS.value,
        r"\b(shp(?:at|ca|pa|ss)_[a-fA-F0-9]{32})\b",
        ("shpat_", "shpca_", "shppa_", "shpss_"),
    ),
    # ---------- messaging ----------
    DetectorSpec(
        "slack_token",
        "Slack token",
        "Slack",
        SecretGroup.MESSAGING.value,
        r"\b(xox[baprs]-[0-9A-Za-z\-]{10,250})\b",
        ("xoxb-", "xoxa-", "xoxp-", "xoxr-", "xoxs-"),
    ),
    DetectorSpec(
        "slack_webhook",
        "Slack webhook",
        "Slack",
        SecretGroup.MESSAGING.value,
        r"(https://hooks\.slack\.com/services/T[A-Z0-9]{8,12}/B[A-Z0-9]{8,12}/[A-Za-z0-9]{20,30})",
        ("hooks.slack.com/services/",),
    ),
    DetectorSpec(
        "discord_webhook",
        "Discord webhook",
        "Discord",
        SecretGroup.MESSAGING.value,
        r"(https://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/[0-9]{17,20}/[A-Za-z0-9_\-]{60,72})",
        ("/api/webhooks/",),
    ),
    DetectorSpec(
        "telegram_bot_token",
        "Telegram bot token",
        "Telegram",
        SecretGroup.MESSAGING.value,
        r"\b([0-9]{8,10}:AA[A-Za-z0-9_\-]{33})\b",
        (":AA",),
    ),
    DetectorSpec(
        "sendgrid_api_key",
        "SendGrid API key",
        "Twilio SendGrid",
        SecretGroup.MESSAGING.value,
        r"\b(SG\.[A-Za-z0-9_\-]{22}\.[A-Za-z0-9_\-]{43})\b",
        ("SG.",),
    ),
    DetectorSpec(
        "twilio_api_key",
        "Twilio API key",
        "Twilio",
        SecretGroup.MESSAGING.value,
        r"\b(SK[0-9a-fA-F]{32})\b",
        ("SK",),
    ),
    DetectorSpec(
        "mailgun_api_key",
        "Mailgun API key",
        "Mailgun",
        SecretGroup.MESSAGING.value,
        r"\b(key-[0-9a-zA-Z]{32})\b",
        ("key-",),
    ),
    DetectorSpec(
        "mailchimp_api_key",
        "Mailchimp API key",
        "Mailchimp",
        SecretGroup.MESSAGING.value,
        r"\b([0-9a-f]{32}-us[0-9]{1,2})\b",
        ("-us",),
    ),
    # ---------- ai ----------
    DetectorSpec(
        "openai_api_key",
        "OpenAI API key",
        "OpenAI",
        SecretGroup.AI.value,
        r"\b(sk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_\-]{20,}T3BlbkFJ[A-Za-z0-9_\-]{20,})\b",
        ("T3BlbkFJ",),
    ),
    DetectorSpec(
        "anthropic_api_key",
        "Anthropic API key",
        "Anthropic",
        SecretGroup.AI.value,
        r"\b(sk-ant-(?:api|admin)[0-9]{2}-[A-Za-z0-9_\-]{80,120})\b",
        ("sk-ant-",),
    ),
    # ---------- auth ----------
    DetectorSpec(
        "private_key",
        "Private key",
        "",
        SecretGroup.AUTH.value,
        rf"(-----BEGIN {_PEM_KIND}-----[\s\S]{{0,8000}}?-----END {_PEM_KIND}-----|-----BEGIN {_PEM_KIND}-----)",
        ("PRIVATE KEY",),
        validator=Validator.PRIVATE_KEY.value,
    ),
    DetectorSpec(
        "jwt",
        "JSON web token",
        "",
        SecretGroup.AUTH.value,
        r"\b(eyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,})",
        ("eyJ",),
        validator=Validator.JWT.value,
    ),
    DetectorSpec(
        "credential_url",
        "Credentials in a URL",
        "",
        SecretGroup.AUTH.value,
        rf"\b((?:https?|ftps?|ssh|sftp)://{_URL_USER}:{_URL_PASS}@{_URL_HOST})",
        ("://",),
        validator=Validator.CREDENTIAL_URL.value,
    ),
    DetectorSpec(
        "vault_token",
        "Vault token",
        "HashiCorp",
        SecretGroup.AUTH.value,
        r"\b(hvs\.[A-Za-z0-9_\-]{24,})\b",
        ("hvs.",),
    ),
    DetectorSpec(
        "age_secret_key",
        "age secret key",
        "",
        SecretGroup.AUTH.value,
        r"\b(AGE-SECRET-KEY-1[A-Z0-9]{58})\b",
        ("AGE-SECRET-KEY-1",),
    ),
    # ---------- data ----------
    DetectorSpec(
        "database_url",
        "Database connection string",
        "",
        SecretGroup.DATA.value,
        rf"\b((?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|rediss?|amqps?|mssql|clickhouse)://{_URL_USER}:{_URL_PASS}@{_URL_HOST}(?:/[^\s\"'<>`\\]{{0,200}})?)",
        ("://",),
        validator=Validator.CREDENTIAL_URL.value,
    ),
    # ---------- platform ----------
    DetectorSpec(
        "sentry_dsn",
        "Sentry DSN",
        "Sentry",
        SecretGroup.PLATFORM.value,
        r"\b(https://[0-9a-f]{32}(?::[0-9a-f]{32})?@[a-z0-9\-]+(?:\.[a-z0-9\-]+)+/[0-9]{1,10})\b",
        ("https://",),
        public=True,
        validator=Validator.NONE.value,
    ),
    DetectorSpec(
        "mapbox_secret_token",
        "Mapbox secret token",
        "Mapbox",
        SecretGroup.PLATFORM.value,
        r"\b(sk\.eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,})\b",
        ("sk.eyJ",),
    ),
    DetectorSpec(
        "mapbox_public_token",
        "Mapbox public token",
        "Mapbox",
        SecretGroup.PLATFORM.value,
        r"\b(pk\.eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,})\b",
        ("pk.eyJ",),
        public=True,
        validator=Validator.NONE.value,
    ),
    DetectorSpec(
        "doppler_token",
        "Doppler token",
        "Doppler",
        SecretGroup.PLATFORM.value,
        r"\b(dp\.(?:pt|st|ct|sa)\.[A-Za-z0-9]{40,44})\b",
        ("dp.pt.", "dp.st.", "dp.ct.", "dp.sa."),
    ),
    DetectorSpec(
        "linear_api_key",
        "Linear API key",
        "Linear",
        SecretGroup.PLATFORM.value,
        r"\b(lin_api_[A-Za-z0-9]{40})\b",
        ("lin_api_",),
    ),
    DetectorSpec(
        "notion_token",
        "Notion token",
        "Notion",
        SecretGroup.PLATFORM.value,
        r"\b((?:secret|ntn)_[A-Za-z0-9]{43,50})\b",
        ("secret_", "ntn_"),
    ),
    DetectorSpec(
        "figma_token",
        "Figma token",
        "Figma",
        SecretGroup.PLATFORM.value,
        r"\b(figd_[A-Za-z0-9_\-]{40,})\b",
        ("figd_",),
    ),
    DetectorSpec(
        "postman_api_key",
        "Postman API key",
        "Postman",
        SecretGroup.PLATFORM.value,
        r"\b(PMAK-[a-f0-9]{24}-[a-f0-9]{34})\b",
        ("PMAK-",),
    ),
    DetectorSpec(
        "grafana_token",
        "Grafana token",
        "Grafana",
        SecretGroup.PLATFORM.value,
        r"\b(glsa_[A-Za-z0-9]{32}_[a-f0-9]{8}|glc_[A-Za-z0-9+/=]{32,})\b",
        ("glsa_", "glc_"),
    ),
    # ---------- contact ----------
    DetectorSpec(
        "email",
        "Email address",
        "",
        SecretGroup.CONTACT.value,
        r"\b([A-Za-z0-9](?:[A-Za-z0-9._%+\-]{0,62}[A-Za-z0-9])?@[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?)*\.[A-Za-z]{2,24})\b",
        ("@",),
        public=True,
        validator=Validator.EMAIL.value,
    ),
)

DETECTORS_BY_KEY: dict[str, DetectorSpec] = {d.key: d for d in DETECTORS}
DETECTOR_KEYS: tuple[str, ...] = tuple(d.key for d in DETECTORS)
DETECTOR_LABELS: dict[str, str] = {d.key: d.label for d in DETECTORS}

# documentation values
PLACEHOLDER_MARKS: tuple[str, ...] = (
    "example",
    "xxxx",
    "your_",
    "yourkey",
    "your-",
    "changeme",
    "placeholder",
    "dummy",
    "sample",
    "insert_",
    "replace_",
    "1234567890",
    "abcdefgh",
    "00000000",
)

# documentation passwords
PLACEHOLDER_PASSWORDS: frozenset[str] = frozenset(
    {
        "password",
        "pass",
        "passwd",
        "pwd",
        "secret",
        "changeme",
        "xxx",
        "xxxx",
        "yourpassword",
        "your_password",
        "your-password",
        "<password>",
        "[password]",
        "password123",
        "123456",
    }
)

# documentation local parts
PLACEHOLDER_LOCAL_PARTS: frozenset[str] = frozenset(
    {
        "user",
        "username",
        "email",
        "name",
        "yourname",
        "youremail",
        "your.name",
        "your.email",
        "someone",
        "firstname",
        "lastname",
        "first.last",
        "john.doe",
        "jane.doe",
        "johndoe",
        "janedoe",
        "example",
        "test",
        "foo",
        "bar",
        "abc",
        "xyz",
        "sample",
        "demo",
        "git",
    }
)

EXAMPLE_DOMAINS: frozenset[str] = frozenset(
    {
        "example.com",
        "example.org",
        "example.net",
        "domain.com",
        "email.com",
        "yourdomain.com",
        "yourcompany.com",
        "company.com",
        "test.com",
        "mysite.com",
        "site.com",
        "server.com",
        "host.com",
        "localhost",
        "localhost.localdomain",
        "sentry.io",
        "w3.org",
    }
)

# logo@2x.png is a file name
FILE_EXTENSIONS: frozenset[str] = frozenset(
    {
        "png",
        "jpg",
        "jpeg",
        "gif",
        "svg",
        "webp",
        "avif",
        "ico",
        "js",
        "mjs",
        "cjs",
        "css",
        "json",
        "html",
        "htm",
        "map",
        "woff",
        "woff2",
        "ttf",
        "otf",
        "eot",
        "mp4",
        "webm",
        "mp3",
        "pdf",
        "xml",
        "txt",
        "md",
    }
)

TEMPLATE_MARKS: tuple[str, ...] = ("{{", "${", "<%", "%7b", "[[", "{%")

__all__ = [
    "BACKFILL_SCANS_PER_TICK",
    "BODY_CAP_BYTES",
    "CONTEXT_RADIUS",
    "DETECTORS",
    "DETECTORS_BY_KEY",
    "DETECTOR_KEYS",
    "DETECTOR_LABELS",
    "DROP_REASON_LABELS",
    "EXAMPLE_DOMAINS",
    "FILE_EXTENSIONS",
    "GROUP_LABELS",
    "GROUP_ORDER",
    "MAX_CONTEXT_LENGTH",
    "MAX_SIGHTINGS_PER_SECRET",
    "MAX_SIGHTINGS_SHOWN",
    "MAX_SUBJECT_LENGTH",
    "MAX_VALUE_LENGTH",
    "MINER_SOURCE_LABELS",
    "MIN_ENTROPY_BITS",
    "MIN_ENTROPY_LENGTH",
    "PLACEHOLDER_LOCAL_PARTS",
    "PLACEHOLDER_MARKS",
    "PLACEHOLDER_PASSWORDS",
    "SOURCE_LABELS",
    "STATE_LABELS",
    "STATE_ORDER",
    "STATE_TONES",
    "TEMPLATE_MARKS",
    "WRITE_BATCH",
    "DetectorSpec",
    "DropReason",
    "MinerSource",
    "SecretGroup",
    "SecretSource",
    "SecretState",
    "Validator",
]
