from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, advanced


class AiDetectionConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="AI detection",
        description=(
            "Identify model servers, AI gateways, AI applications and MCP servers "
            "on every web asset. About 55 requests per web asset."
        ),
    )
    mcp_paths: bool = Field(
        default=True,
        title="MCP paths",
        description="Send an MCP handshake to /mcp and /api/mcp on every web asset.",
    )
    max_minutes: int = Field(
        default=30,
        ge=1,
        le=480,
        title="Time budget (min)",
        description="Stop starting batches after this many minutes. Web assets not reached are reported.",
    )
    max_assets: int = advanced(
        5000,
        ge=1,
        le=100_000,
        title="Web asset budget",
        description="Stop after this many web assets. Non-standard ports are probed first.",
    )


BATCH_ASSETS = 8
JULIUS_CONCURRENCY = 10
BATCH_SECONDS_PER_ASSET = 45
