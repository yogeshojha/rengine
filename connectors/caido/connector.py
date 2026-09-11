"""Caido, through the HAR importer until a native plugin exists."""

from __future__ import annotations

from connectors.base import ProxyConnector, SetupStep
from shared.definitions.connectors import ConnectorKind


class CaidoConnector(ProxyConnector):
    kind = ConnectorKind.CAIDO.value
    title = "Caido"
    vendor = "Caido Labs"
    description = (
        "Receives proxied traffic from Caido. Export your HTTP history and import it, "
        "or post batches from a workflow."
    )
    docs_url = "https://developer.caido.io/"
    source_path = "clients/har"
    supports_scope_push = True

    def setup(self, *, endpoint: str, secret: str) -> list[SetupStep]:
        return [
            SetupStep(
                title="Export what you have browsed",
                detail=(
                    "In Caido, open HTTP History, select the requests worth keeping and "
                    "export them as HAR. Nothing but the shape of each request leaves "
                    "your machine: headers, cookies and bodies stay in Caido."
                ),
            ),
            SetupStep(
                title="Import it",
                detail=(
                    "The importer needs only Python 3. Run it again whenever you have "
                    "browsed more; reNgine folds repeats into one shape."
                ),
                code=(
                    "python3 clients/har/rengine_har.py \\\n"
                    f"  --endpoint {endpoint} \\\n"
                    f"  --token {secret} \\\n"
                    "  --client caido \\\n"
                    "  history.har"
                ),
                lang="shell",
            ),
            SetupStep(
                title="Or post batches yourself",
                detail=(
                    "This is the whole contract, if you would rather drive it from a "
                    "Caido workflow or a script of your own. The token is shown once."
                ),
                code=(
                    f"curl -X POST {endpoint} \\\n"
                    f"  -H 'Authorization: Bearer {secret}' \\\n"
                    "  -H 'Content-Type: application/json' \\\n"
                    '  -d \'{"client":"caido","items":[{"url":"https://target/admin/","method":"GET","status_code":200,"authenticated":true,"source_tool":"proxy"}]}\''
                ),
                lang="shell",
            ),
            SetupStep(
                title="No native plugin yet",
                detail=(
                    "A Caido plugin has not been built. The importer is the supported "
                    "path and works with any proxy that exports HAR."
                ),
            ),
        ]
