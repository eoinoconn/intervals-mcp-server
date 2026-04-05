"""
Tests for the auth module — IntervalsTokenVerifier and get_auth_api_key.
"""
import asyncio
import os
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test_env_key")
os.environ.setdefault("ATHLETE_ID", "i1")


from intervals_mcp_server.auth import IntervalsTokenVerifier, get_auth_api_key


# --- IntervalsTokenVerifier tests ---

def test_verify_token_returns_access_token():
    """A non-empty token should produce a valid AccessToken."""
    verifier = IntervalsTokenVerifier()
    result = asyncio.run(verifier.verify_token("my_api_key_123"))
    assert result is not None
    assert result.token == "my_api_key_123"
    assert result.client_id == "intervals-icu-user"
    assert result.scopes == []


def test_verify_token_empty_returns_none():
    """An empty token should return None (unauthenticated)."""
    verifier = IntervalsTokenVerifier()
    result = asyncio.run(verifier.verify_token(""))
    assert result is None


# --- get_auth_api_key tests ---

def test_get_auth_api_key_returns_empty_no_context():
    """When no bearer token is in context, should return empty string."""
    result = get_auth_api_key()
    assert result == ""
