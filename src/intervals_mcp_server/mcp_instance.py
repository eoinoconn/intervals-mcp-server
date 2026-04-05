"""
Shared MCP instance module.

This module provides a shared FastMCP instance that can be imported by both
the server module and tool modules without creating cyclic imports.
"""

import os

from mcp.server.fastmcp import FastMCP  # pylint: disable=import-error

from intervals_mcp_server.api.client import setup_api_client
from intervals_mcp_server.auth import IntervalsTokenVerifier

# Only enable token verification when running over HTTP transports (SSE/streamable-http).
# For stdio transport (local Claude Desktop), no auth is needed.
_transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
_token_verifier = IntervalsTokenVerifier() if _transport in ("sse", "streamable-http", "http") else None

mcp: FastMCP = FastMCP(  # pylint: disable=invalid-name
    "intervals-icu",
    lifespan=setup_api_client,
    host=os.getenv("FASTMCP_HOST", "127.0.0.1"),
    token_verifier=_token_verifier,
)
