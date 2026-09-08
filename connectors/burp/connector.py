"""Burp Suite, through a Montoya extension."""

from __future__ import annotations

from connectors.base import ProxyConnector, SetupStep
from shared.definitions.connectors import ConnectorKind


class BurpConnector(ProxyConnector):
    kind = ConnectorKind.BURP.value
    title = "Burp Suite"
    vendor = "PortSwigger"
    description = (
        "Receives proxied traffic from Burp Suite. "
        "Supported on Community and Professional."
    )
    docs_url = (
        "https://portswigger.net/burp/documentation/desktop/extend-burp/extensions"
    )
    source_path = "clients/burp"
    supports_scope_push = True

    def setup(self, *, endpoint: str, secret: str) -> list[SetupStep]:
        return [
            SetupStep(
                title="Build the extension",
                detail="The extension is not published to the BApp Store yet. Build the jar from clients/burp in the reNgine repository. A JDK 17 or later is the only requirement.",
                code="cd clients/burp && ./build.sh",
                lang="shell",
            ),
            SetupStep(
                title="Load it into Burp",
                detail="Extensions \u2192 Installed \u2192 Add, extension type Java, then select the jar the build printed.",
            ),
            SetupStep(
                title="Connect it",
                detail="Open the reNgine tab in Burp, enter these values and press Test connection. The token is shown once.",
                code=f"Endpoint  {endpoint}\nToken     {secret}",
                lang="shell",
            ),
            SetupStep(
                title="Start capturing",
                detail="Enable Send captured requests, then request a page from a target in this project. The connector state changes to Receiving.",
            ),
        ]
