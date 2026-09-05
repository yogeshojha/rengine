import shlex

from pydantic import BaseModel

MAX_TOOL_OPTION_LEN = 1000


def parse_tool_args(raw: str) -> list[str]:
    """shlex-split custom tool args for execution; [] on parse error (validated on save)."""
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


# CLI tools that accept custom args today (HTTP-only providers + scaffolds excluded).
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
        name="assetfinder",
        label="Assetfinder",
        phase="Subdomain Discovery",
        example="--subs-only",
    ),
    ToolSpec(
        name="sublist3r",
        label="Sublist3r",
        phase="Subdomain Discovery",
        example="-v",
    ),
    ToolSpec(
        name="oneforall",
        label="OneForAll",
        phase="Subdomain Discovery",
        example="--takeover False",
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
)

TOOL_NAMES: frozenset[str] = frozenset(t.name for t in SCAN_TOOLS)
