"""
Authentication support for Intervals.icu MCP Server.

When the server runs over SSE/streamable-http, an ``MCP_AUTH_TOKEN``
environment variable acts as a shared secret.  Clients must send this
token as a Bearer token in the Authorization header.  The middleware
validates the token and rejects requests that don't match with a 401.

When ``MCP_AUTH_TOKEN`` is not set, the middleware is a no-op so that
local/stdio usage remains frictionless.
"""

import hmac
import logging
import os

from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger("intervals_icu_mcp_server")


class BearerTokenMiddleware:
    """ASGI middleware that gates access via a shared Bearer token."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.expected_token: str | None = os.getenv("MCP_AUTH_TOKEN") or None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Only gate HTTP / WebSocket requests; let lifespan through.
        if self.expected_token and scope["type"] in ("http", "websocket"):
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()
            token = auth_header[7:] if auth_header.startswith("Bearer ") else ""

            if not hmac.compare_digest(token, self.expected_token):
                response = PlainTextResponse("Unauthorized", status_code=401)
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)
