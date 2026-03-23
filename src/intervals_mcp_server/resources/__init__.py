"""
MCP resources for Intervals.icu MCP Server.

This module registers all available MCP resources with the FastMCP server instance.
"""

from intervals_mcp_server.resources.guide import usage_guide  # noqa: F401

__all__ = [
    "usage_guide",
]
