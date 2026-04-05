"""
Tests for the auth module — BearerTokenMiddleware and get_auth_api_key.
"""
import asyncio
import os
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test_env_key")
os.environ.setdefault("ATHLETE_ID", "i1")


from intervals_mcp_server.auth import BearerTokenMiddleware, get_auth_api_key


# --- get_auth_api_key tests ---

def test_get_auth_api_key_returns_empty_no_context():
    """When no bearer token is in context, should return empty string."""
    result = get_auth_api_key()
    assert result == ""


# --- BearerTokenMiddleware tests ---

def test_middleware_extracts_bearer_token():
    """Middleware should set the context var from Authorization header."""
    captured_token = None

    async def inner_app(scope, receive, send):
        nonlocal captured_token
        captured_token = get_auth_api_key()

    middleware = BearerTokenMiddleware(inner_app)

    async def run():
        scope = {
            "type": "http",
            "headers": [(b"authorization", b"Bearer my_intervals_token_123")],
        }
        await middleware(scope, None, None)

    asyncio.run(run())
    assert captured_token == "my_intervals_token_123"


def test_middleware_no_auth_header():
    """Middleware should set empty token when no auth header."""
    captured_token = None

    async def inner_app(scope, receive, send):
        nonlocal captured_token
        captured_token = get_auth_api_key()

    middleware = BearerTokenMiddleware(inner_app)

    async def run():
        scope = {"type": "http", "headers": []}
        await middleware(scope, None, None)

    asyncio.run(run())
    assert captured_token == ""


def test_middleware_non_bearer_auth():
    """Middleware should ignore non-Bearer auth headers."""
    captured_token = None

    async def inner_app(scope, receive, send):
        nonlocal captured_token
        captured_token = get_auth_api_key()

    middleware = BearerTokenMiddleware(inner_app)

    async def run():
        scope = {
            "type": "http",
            "headers": [(b"authorization", b"Basic dXNlcjpwYXNz")],
        }
        await middleware(scope, None, None)

    asyncio.run(run())
    assert captured_token == ""


def test_middleware_resets_after_request():
    """Token context var should be reset after request completes."""
    middleware = BearerTokenMiddleware(
        lambda scope, receive, send: asyncio.sleep(0)
    )

    async def run():
        scope = {
            "type": "http",
            "headers": [(b"authorization", b"Bearer temp_token")],
        }
        await middleware(scope, None, None)
        # After middleware completes, token should be back to default
        assert get_auth_api_key() == ""

    asyncio.run(run())
