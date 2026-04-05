"""
MCP resources for Intervals.icu MCP Server.

This module registers all available MCP resources with the FastMCP server instance.
"""

from intervals_mcp_server.resources.guide import coaching_context_protocol  # noqa: F401

__all__ = [
    "coaching_context_protocol",
]
