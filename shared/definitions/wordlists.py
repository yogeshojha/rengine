"""The wordlist vocabulary: what a guessing stage reads, and where it may read it from."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

BUILTIN_ROOT = "/app/tools/data"
CUSTOM_ROOT = "/app/wordlists/custom"

MAX_WORDLIST_BYTES = 8 * 1024 * 1024
MAX_WORDLIST_UPLOAD = 10
# a DNS label is 63 characters; a longer line is not a word
MAX_WORD_LENGTH = 63
MAX_SLUG_LENGTH = 64


class WordlistOrigin(StrEnum):
    BUILTIN = "builtin"
    CUSTOM = "custom"


class WordlistKind(StrEnum):
    """What the words are, so a stage never offers a list it cannot use."""

    SUBDOMAIN = "subdomain"
    VHOST = "vhost"
    CONTENT = "content"


KIND_LABELS: dict[str, str] = {
    WordlistKind.SUBDOMAIN.value: "Subdomain names",
    WordlistKind.VHOST.value: "Virtual host names",
    WordlistKind.CONTENT.value: "Paths and files",
}


class BuiltinWordlist(BaseModel):
    slug: str
    filename: str
    name: str
    kind: str
    description: str


# shipped with the image, indexed on first read so they appear beside uploads
BUILTIN_WORDLISTS: tuple[BuiltinWordlist, ...] = (
    BuiltinWordlist(
        slug="common-subdomains",
        filename="subdomains.txt",
        name="Common subdomains",
        kind=WordlistKind.SUBDOMAIN.value,
        description=(
            "Names ranked by how often they appear in public DNS data, best first. "
            "A smaller word budget reads from the top of this ranking."
        ),
    ),
    BuiltinWordlist(
        slug="common-vhosts",
        filename="vhosts.txt",
        name="Common virtual hosts",
        kind=WordlistKind.VHOST.value,
        description="Short list of host names worth trying against an address directly.",
    ),
)

DEFAULT_WORDLIST: dict[str, str] = {
    WordlistKind.SUBDOMAIN.value: "common-subdomains",
    WordlistKind.VHOST.value: "common-vhosts",
}


def slugify(value: str) -> str:
    out = "".join(c if c.isalnum() else "-" for c in value.strip().lower())
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")[:MAX_SLUG_LENGTH]


__all__ = [
    "BUILTIN_ROOT",
    "BUILTIN_WORDLISTS",
    "CUSTOM_ROOT",
    "DEFAULT_WORDLIST",
    "KIND_LABELS",
    "MAX_SLUG_LENGTH",
    "MAX_WORDLIST_BYTES",
    "MAX_WORDLIST_UPLOAD",
    "MAX_WORD_LENGTH",
    "BuiltinWordlist",
    "WordlistKind",
    "WordlistOrigin",
    "slugify",
]
