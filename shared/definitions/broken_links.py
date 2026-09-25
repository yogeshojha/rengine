"""Broken-link hijacking: an embedded resource loaded from a buyable domain."""

from __future__ import annotations

from enum import StrEnum

from shared.definitions.vulnerabilities import Severity


class LinkKind(StrEnum):
    SCRIPT = "script"
    IFRAME = "iframe"
    STYLESHEET = "stylesheet"
    IMAGE = "image"
    LINK = "link"


KIND_LABELS: dict[str, str] = {
    LinkKind.SCRIPT.value: "Script",
    LinkKind.IFRAME.value: "Frame",
    LinkKind.STYLESHEET.value: "Stylesheet",
    LinkKind.IMAGE.value: "Image",
    LinkKind.LINK.value: "Link",
}

KIND_SEVERITY: dict[str, str] = {
    LinkKind.SCRIPT.value: Severity.HIGH.value,
    LinkKind.IFRAME.value: Severity.HIGH.value,
    LinkKind.STYLESHEET.value: Severity.MEDIUM.value,
    LinkKind.IMAGE.value: Severity.LOW.value,
    LinkKind.LINK.value: Severity.LOW.value,
}

KIND_RANK: dict[str, int] = {
    LinkKind.SCRIPT.value: 4,
    LinkKind.IFRAME.value: 3,
    LinkKind.STYLESHEET.value: 2,
    LinkKind.IMAGE.value: 1,
    LinkKind.LINK.value: 0,
}

TEMPLATE_ID = "broken-link-hijacking"
TEMPLATE_NAME = "Broken link hijacking"
FINDING_TAGS: tuple[str, ...] = ("takeover", "broken-link", "supply-chain")

BODY_SCAN_BYTES = 512 * 1024
MAX_PAGES = 2000
MAX_DOMAINS = 400
RESOLVE_WORKERS = 16
RESOLVE_QUORUM = 2
RESOLVERS: tuple[str, ...] = ("1.1.1.1", "8.8.8.8", "9.9.9.9", "208.67.222.222")
