"""Burp Suite, through a Montoya extension."""

from __future__ import annotations

from connectors.base import ProxyConnector, SetupStep
from shared.definitions.connectors import ConnectorKind, SetupControl


class BurpConnector(ProxyConnector):
    kind = ConnectorKind.BURP.value
    title = "Burp Suite"
    client_pattern = "rengine-connector-*.jar"

    def setup(self) -> list[SetupStep]:
        return [
            SetupStep(
                title="Download the extension",
                detail="Burp Suite Community or Professional. JRE 17 or later.",
                control=SetupControl.DOWNLOAD.value,
            ),
            SetupStep(
                title="Load it into Burp",
                detail="Extensions, Installed, Add. Extension type Java. Select the jar.",
            ),
            SetupStep(
                title="Paste the endpoint and the token",
                detail="Open the reNgine tab in Burp. Press Save and test.",
                control=SetupControl.CREDENTIALS.value,
            ),
            SetupStep(
                title="Select the target",
                detail="Select it under Working on. Press Apply scope to Burp. Tick Send captured requests to reNgine.",
            ),
        ]
