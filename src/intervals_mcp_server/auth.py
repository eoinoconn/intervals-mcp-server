"""
Authentication support for Intervals.icu MCP Server.

Provides a TokenVerifier that accepts any Intervals.icu API key passed as a
Bearer token.  When the server runs over SSE/streamable-http, Claude sends
the user's API key in the Authorization header.  The verifier simply passes
the raw token through so that tool functions can retrieve it via
``get_auth_api_key()``.
"""

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken


class IntervalsTokenVerifier:
    """Accept any non-empty bearer token as a valid Intervals.icu API key."""

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token:
            return None
        return AccessToken(
            token=token,
            client_id="intervals-icu-user",
            scopes=[],
        )


def get_auth_api_key() -> str:
    """Return the API key from the current request's auth context.

    Returns the bearer token if present (i.e. when the server runs over
    SSE/streamable-http and the client supplies a token).  Returns an empty
    string when no token is available — callers should fall back to their
    own ``api_key`` parameter or the ``API_KEY`` environment variable.
    """
    access_token = get_access_token()
    if access_token and access_token.token:
        return access_token.token
    return ""
