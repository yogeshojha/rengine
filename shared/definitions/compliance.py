"""Findings mapped to control frameworks. A mapping is evidence for an auditor, never a compliance verdict."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Framework(StrEnum):
    OWASP = "owasp_top10"
    PCI = "pci_dss"
    ISO = "iso_27001"
    NIST = "nist_csf"


@dataclass(frozen=True)
class Control:
    id: str
    title: str
    note: str = ""


@dataclass(frozen=True)
class FrameworkSpec:
    key: str
    name: str
    version: str
    description: str
    url: str
    scope_note: str
    controls: tuple[Control, ...]

    @property
    def by_id(self) -> dict[str, Control]:
        return {c.id: c for c in self.controls}


_UNMAPPED_NOTE = (
    "Checks that fired without a weakness classification are listed as unmapped."
)

OWASP = FrameworkSpec(
    key=Framework.OWASP.value,
    name="OWASP Top 10",
    version="2021",
    description="The ten most critical web application security risks.",
    url="https://owasp.org/Top10/",
    scope_note=(
        "Mapped from the weakness class each check declares. An unauthenticated external "
        "scan cannot observe every category, so an empty category is not evidence of absence."
    ),
    controls=(
        Control(
            "A01", "Broken Access Control", "Authorisation not enforced on a resource."
        ),
        Control("A02", "Cryptographic Failures", "Data exposed in transit or at rest."),
        Control("A03", "Injection", "Untrusted input reaching an interpreter."),
        Control("A04", "Insecure Design", "A control the design never provided."),
        Control(
            "A05",
            "Security Misconfiguration",
            "A service left in a state its operator did not intend.",
        ),
        Control(
            "A06",
            "Vulnerable and Outdated Components",
            "Software with a published vulnerability.",
        ),
        Control(
            "A07",
            "Identification and Authentication Failures",
            "Identity not established or not protected.",
        ),
        Control(
            "A08",
            "Software and Data Integrity Failures",
            "Code or data trusted without verification.",
        ),
        Control(
            "A09",
            "Security Logging and Monitoring Failures",
            "Events not recorded or exposed.",
        ),
        Control(
            "A10",
            "Server-Side Request Forgery",
            "The server fetches a location an attacker chooses.",
        ),
    ),
)

PCI = FrameworkSpec(
    key=Framework.PCI.value,
    name="PCI DSS",
    version="4.0",
    description="Payment Card Industry Data Security Standard.",
    url="https://www.pcisecuritystandards.org/",
    scope_note=(
        "Covers only the requirements an external scan can produce evidence for. "
        "This is not an ASV scan and does not satisfy requirement 11.3.2."
    ),
    controls=(
        Control(
            "2",
            "Apply secure configurations",
            "Defaults, unnecessary services and exposed management.",
        ),
        Control(
            "4", "Protect data in transit", "Strong cryptography on public networks."
        ),
        Control(
            "6",
            "Develop and maintain secure systems",
            "Known vulnerabilities and secure software.",
        ),
        Control(
            "7", "Restrict access by business need", "Access to system components."
        ),
        Control(
            "8",
            "Identify users and authenticate access",
            "Credentials and authentication.",
        ),
        Control(
            "11",
            "Test security regularly",
            "Vulnerability scanning and external testing.",
        ),
    ),
)

ISO = FrameworkSpec(
    key=Framework.ISO.value,
    name="ISO/IEC 27001 Annex A",
    version="2022",
    description="Information security controls.",
    url="https://www.iso.org/standard/27001",
    scope_note=(
        "Technical controls only. Organisational, people and physical controls are out of scope for a scanner."
    ),
    controls=(
        Control("A.5.15", "Access control", "Rules for physical and logical access."),
        Control(
            "A.5.17",
            "Authentication information",
            "Allocation and management of secrets.",
        ),
        Control(
            "A.8.8",
            "Management of technical vulnerabilities",
            "Vulnerabilities identified and addressed.",
        ),
        Control(
            "A.8.9",
            "Configuration management",
            "Secure configuration of hardware and software.",
        ),
        Control("A.8.20", "Networks security", "Networks managed and controlled."),
        Control(
            "A.8.21",
            "Security of network services",
            "Security mechanisms of network services.",
        ),
        Control(
            "A.8.24", "Use of cryptography", "Rules for effective use of cryptography."
        ),
        Control("A.8.28", "Secure coding", "Secure coding principles applied."),
    ),
)

NIST = FrameworkSpec(
    key=Framework.NIST.value,
    name="NIST Cybersecurity Framework",
    version="2.0",
    description="Outcomes for managing cybersecurity risk.",
    url="https://www.nist.gov/cyberframework",
    scope_note=(
        "External discovery evidence for the Identify and Protect functions. "
        "Govern, Respond and Recover are not observable from a scan."
    ),
    controls=(
        Control("ID.AM", "Asset Management", "Assets are inventoried and understood."),
        Control(
            "ID.RA",
            "Risk Assessment",
            "Vulnerabilities are identified and risk understood.",
        ),
        Control(
            "PR.AA",
            "Identity Management and Access Control",
            "Access is limited to authorised users.",
        ),
        Control("PR.DS", "Data Security", "Data is protected in transit and at rest."),
        Control(
            "PR.PS", "Platform Security", "Hardware and software are managed securely."
        ),
        Control(
            "PR.IR",
            "Technology Infrastructure Resilience",
            "Infrastructure is protected.",
        ),
        Control(
            "DE.CM", "Continuous Monitoring", "Assets are monitored for adverse events."
        ),
    ),
)

FRAMEWORKS: tuple[FrameworkSpec, ...] = (OWASP, PCI, ISO, NIST)
FRAMEWORK_BY_KEY: dict[str, FrameworkSpec] = {f.key: f for f in FRAMEWORKS}
FRAMEWORK_KEYS: tuple[str, ...] = tuple(f.key for f in FRAMEWORKS)
DEFAULT_FRAMEWORKS: list[str] = [Framework.OWASP.value]

# the OWASP 2021 category each weakness class belongs to, from the project's own mapping
_OWASP_CWES: dict[str, tuple[int, ...]] = {
    "A01": (
        22,
        23,
        35,
        59,
        200,
        201,
        219,
        275,
        276,
        284,
        285,
        352,
        359,
        377,
        402,
        425,
        441,
        497,
        538,
        540,
        548,
        552,
        566,
        601,
        639,
        651,
        668,
        706,
        862,
        863,
        913,
        922,
        1275,
    ),
    "A02": (
        261,
        296,
        310,
        319,
        321,
        322,
        323,
        324,
        325,
        326,
        327,
        328,
        329,
        330,
        331,
        335,
        336,
        337,
        338,
        340,
        347,
        523,
        720,
        757,
        759,
        760,
        780,
        818,
        916,
    ),
    "A03": (
        20,
        74,
        75,
        77,
        78,
        79,
        80,
        83,
        87,
        88,
        89,
        90,
        91,
        93,
        94,
        95,
        96,
        97,
        98,
        99,
        100,
        113,
        116,
        138,
        184,
        470,
        471,
        564,
        610,
        643,
        644,
        652,
        917,
    ),
    "A04": (
        73,
        183,
        209,
        213,
        235,
        256,
        257,
        266,
        269,
        280,
        311,
        312,
        313,
        316,
        419,
        430,
        434,
        444,
        451,
        472,
        501,
        522,
        525,
        539,
        579,
        598,
        602,
        642,
        646,
        650,
        653,
        656,
        657,
        799,
        807,
        840,
        841,
        927,
        1021,
        1173,
    ),
    "A05": (
        2,
        11,
        13,
        15,
        16,
        260,
        315,
        520,
        526,
        537,
        541,
        547,
        611,
        614,
        756,
        776,
        942,
        1004,
        1032,
        1174,
    ),
    "A06": (937, 1035, 1104),
    "A07": (
        255,
        259,
        287,
        288,
        290,
        294,
        295,
        297,
        300,
        302,
        304,
        306,
        307,
        346,
        384,
        521,
        613,
        620,
        640,
        798,
        940,
        1216,
    ),
    "A08": (345, 353, 426, 494, 502, 565, 784, 829, 830, 915),
    "A09": (117, 223, 532, 778),
    "A10": (918,),
}

OWASP_BY_CWE: dict[int, str] = {
    cwe: control for control, cwes in _OWASP_CWES.items() for cwe in cwes
}

# 2024 CWE Top 25 most dangerous software weaknesses, in rank order
CWE_TOP_25: tuple[int, ...] = (
    79,
    787,
    89,
    352,
    22,
    125,
    78,
    416,
    862,
    434,
    94,
    20,
    77,
    287,
    269,
    502,
    200,
    863,
    918,
    119,
    476,
    798,
    190,
    400,
    306,
)
CWE_TOP_25_RANK: dict[int, int] = {c: i + 1 for i, c in enumerate(CWE_TOP_25)}


@dataclass(frozen=True)
class TagRule:
    tags: frozenset[str]
    controls: dict[str, tuple[str, ...]]


# a check with no weakness class still says what it is; its tags carry the mapping
TAG_RULES: tuple[TagRule, ...] = (
    TagRule(
        frozenset(
            {
                "sqli",
                "xss",
                "rce",
                "ssti",
                "lfi",
                "xxe",
                "injection",
                "traversal",
                "crlf",
            }
        ),
        {
            Framework.OWASP.value: ("A03",),
            Framework.PCI.value: ("6",),
            Framework.ISO.value: ("A.8.28",),
            Framework.NIST.value: ("PR.PS",),
        },
    ),
    TagRule(
        frozenset({"ssrf"}),
        {
            Framework.OWASP.value: ("A10",),
            Framework.PCI.value: ("6",),
            Framework.ISO.value: ("A.8.28",),
            Framework.NIST.value: ("PR.PS",),
        },
    ),
    TagRule(
        frozenset({"default-login", "auth-bypass", "unauth", "weak-password"}),
        {
            Framework.OWASP.value: ("A07",),
            Framework.PCI.value: ("8",),
            Framework.ISO.value: ("A.5.17",),
            Framework.NIST.value: ("PR.AA",),
        },
    ),
    TagRule(
        frozenset({"panel", "login", "admin"}),
        {
            Framework.OWASP.value: ("A05",),
            Framework.PCI.value: ("7",),
            Framework.ISO.value: ("A.5.15",),
            Framework.NIST.value: ("PR.AA",),
        },
    ),
    TagRule(
        frozenset({"exposure", "disclosure", "backup", "config", "files", "debug"}),
        {
            Framework.OWASP.value: ("A05",),
            Framework.PCI.value: ("2",),
            Framework.ISO.value: ("A.8.9",),
            Framework.NIST.value: ("PR.DS",),
        },
    ),
    TagRule(
        frozenset({"takeover", "misconfig"}),
        {
            Framework.OWASP.value: ("A05",),
            Framework.PCI.value: ("2",),
            Framework.ISO.value: ("A.8.9",),
            Framework.NIST.value: ("PR.IR",),
        },
    ),
    TagRule(
        frozenset({"ssl", "tls", "weak-cipher", "self-signed", "expired"}),
        {
            Framework.OWASP.value: ("A02",),
            Framework.PCI.value: ("4",),
            Framework.ISO.value: ("A.8.24",),
            Framework.NIST.value: ("PR.DS",),
        },
    ),
    TagRule(
        frozenset({"cve", "kev", "edb", "outdated"}),
        {
            Framework.OWASP.value: ("A06",),
            Framework.PCI.value: ("6",),
            Framework.ISO.value: ("A.8.8",),
            Framework.NIST.value: ("ID.RA",),
        },
    ),
    TagRule(
        frozenset({"network", "ftp", "telnet", "smb", "rdp", "database"}),
        {
            Framework.OWASP.value: ("A05",),
            Framework.PCI.value: ("2",),
            Framework.ISO.value: ("A.8.21",),
            Framework.NIST.value: ("PR.IR",),
        },
    ),
)

# what a discovery run alone is evidence for, findings or not
SURFACE_CONTROLS: dict[str, tuple[str, ...]] = {
    Framework.NIST.value: ("ID.AM", "DE.CM"),
    Framework.ISO.value: ("A.8.20",),
    Framework.PCI.value: ("11",),
}

# the framework control each OWASP category corresponds to elsewhere
_OWASP_ALIGN: dict[str, dict[str, tuple[str, ...]]] = {
    "A01": {
        Framework.PCI.value: ("7",),
        Framework.ISO.value: ("A.5.15",),
        Framework.NIST.value: ("PR.AA",),
    },
    "A02": {
        Framework.PCI.value: ("4",),
        Framework.ISO.value: ("A.8.24",),
        Framework.NIST.value: ("PR.DS",),
    },
    "A03": {
        Framework.PCI.value: ("6",),
        Framework.ISO.value: ("A.8.28",),
        Framework.NIST.value: ("PR.PS",),
    },
    "A04": {
        Framework.PCI.value: ("6",),
        Framework.ISO.value: ("A.8.28",),
        Framework.NIST.value: ("PR.PS",),
    },
    "A05": {
        Framework.PCI.value: ("2",),
        Framework.ISO.value: ("A.8.9",),
        Framework.NIST.value: ("PR.PS",),
    },
    "A06": {
        Framework.PCI.value: ("6",),
        Framework.ISO.value: ("A.8.8",),
        Framework.NIST.value: ("ID.RA",),
    },
    "A07": {
        Framework.PCI.value: ("8",),
        Framework.ISO.value: ("A.5.17",),
        Framework.NIST.value: ("PR.AA",),
    },
    "A08": {
        Framework.PCI.value: ("6",),
        Framework.ISO.value: ("A.8.28",),
        Framework.NIST.value: ("PR.PS",),
    },
    "A09": {
        Framework.PCI.value: ("11",),
        Framework.ISO.value: ("A.8.9",),
        Framework.NIST.value: ("DE.CM",),
    },
    "A10": {
        Framework.PCI.value: ("6",),
        Framework.ISO.value: ("A.8.28",),
        Framework.NIST.value: ("PR.PS",),
    },
}


def map_finding(
    cwe_ids: list[str] | tuple[str, ...] | None,
    tags: list[str] | tuple[str, ...] | None,
) -> dict[str, list[str]]:
    """Every framework control a single finding is evidence for."""
    out: dict[str, set[str]] = {f: set() for f in FRAMEWORK_KEYS}

    for raw in cwe_ids or ():
        number = _cwe_number(raw)
        if number is None:
            continue
        category = OWASP_BY_CWE.get(number)
        if not category:
            continue
        out[Framework.OWASP.value].add(category)
        for framework, controls in _OWASP_ALIGN.get(category, {}).items():
            out[framework].update(controls)

    lowered = {t.strip().lower() for t in tags or () if t}
    for rule in TAG_RULES:
        if lowered & rule.tags:
            for framework, controls in rule.controls.items():
                out[framework].update(controls)

    return {
        framework: sorted(controls, key=_control_order(framework))
        for framework, controls in out.items()
        if controls
    }


def cwe_top_25_rank(cwe_ids: list[str] | tuple[str, ...] | None) -> int | None:
    ranks = [
        CWE_TOP_25_RANK[number]
        for raw in cwe_ids or ()
        if (number := _cwe_number(raw)) is not None and number in CWE_TOP_25_RANK
    ]
    return min(ranks) if ranks else None


def _cwe_number(raw: str | int | None) -> int | None:
    if isinstance(raw, int):
        return raw
    if not raw:
        return None
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    return int(digits) if digits else None


def _control_order(framework: str):
    order = {c.id: i for i, c in enumerate(FRAMEWORK_BY_KEY[framework].controls)}
    return lambda control: order.get(control, len(order))
