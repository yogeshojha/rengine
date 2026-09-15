from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig


class SecretMiningConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Response secret mining",
        description=(
            "Credentials, tokens, keys and contacts read from stored responses. "
            "No request is sent."
        ),
    )
