"""MCP token minting and verification."""

from __future__ import annotations

from shared.utils.bearer import TokenFormat, fingerprint, from_header

_FORMAT = TokenFormat("rngmcp_")
PREFIX = _FORMAT.prefix
mint = _FORMAT.mint
looks_like_token = _FORMAT.looks_like_token

__all__ = ["PREFIX", "fingerprint", "from_header", "looks_like_token", "mint"]
