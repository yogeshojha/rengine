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
    client_file = "rengine-connector-0.1.0.jar"
    supports_scope_push = True

    def setup(self, **_: str) -> list[SetupStep]:
        return [
            SetupStep(
                title="Download the extension",
                detail="Burp Suite Community or Professional. JRE 17 or later.",
            ),
            SetupStep(
                title="Load it into Burp",
                detail="Extensions, Installed, Add. Extension type Java. Select the jar.",
            ),
            SetupStep(
                title="Connect it",
                detail="Open the reNgine tab in Burp. Paste the endpoint and the token. Press Test connection.",
            ),
            SetupStep(
                title="Select the target",
                detail="Select it under Working on. Press Apply scope to Burp. Tick Send captured requests to reNgine.",
            ),
        ]
