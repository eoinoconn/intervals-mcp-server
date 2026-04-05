"""
Authentication support for Intervals.icu MCP Server.

When the server runs over SSE/streamable-http, Claude can send the user's
Intervals.icu API key as a Bearer token in the Authorization header.  A
lightweight ASGI middleware extracts the token and stores it in a context
variable so that tool functions can retrieve it via ``get_auth_api_key()``.
"""

import contextvars

from starlette.types import ASGIApp, Receive, Scope, Send

# Context variable holding the bearer token for the current request.
_bearer_token_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "bearer_token", default=""
)


class BearerTokenMiddleware:
    """ASGI middleware that extracts a Bearer token from the Authorization header."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        token = ""
        if scope["type"] in ("http", "websocket"):
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]

        ctx_token = _bearer_token_var.set(token)
        try:
            await self.app(scope, receive, send)
        finally:
            _bearer_token_var.reset(ctx_token)


def get_auth_api_key() -> str:
    """Return the API key from the current request's Bearer token.

    Returns an empty string when no token is available (e.g. stdio transport).
    Callers should fall back to their own ``api_key`` parameter or the
    ``API_KEY`` environment variable.
    """
    return _bearer_token_var.get()
