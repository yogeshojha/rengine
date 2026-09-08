"""Caido, through a plugin or the ingest endpoint."""

from __future__ import annotations

from connectors.base import ProxyConnector, SetupStep
from shared.definitions.connectors import ConnectorKind


class CaidoConnector(ProxyConnector):
    kind = ConnectorKind.CAIDO.value
    title = "Caido"
    vendor = "Caido Labs"
    description = (
        "Receives proxied traffic from Caido through the plugin or the ingest endpoint."
    )
    docs_url = "https://developer.caido.io/"
    supports_scope_push = True

    def setup(self, *, endpoint: str, secret: str) -> list[SetupStep]:
        return [
            SetupStep(
                title="No plugin is published yet",
                detail="A Caido plugin has not been built. Any client that can post JSON works in the meantime, including a script or a Caido workflow.",
            ),
            SetupStep(
                title="Post batches to the ingest endpoint",
                detail="This is the whole contract. The token is shown once.",
                code=(
                    f"curl -X POST {endpoint} \\\n"
                    f"  -H 'Authorization: Bearer {secret}' \\\n"
                    "  -H 'Content-Type: application/json' \\\n"
                    '  -d \'{"client":"caido","items":[{"url":"https://target/admin/","method":"GET","status_code":200,"authenticated":true,"source_tool":"proxy"}]}\''
                ),
                lang="shell",
            ),
        ]
