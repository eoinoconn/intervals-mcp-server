"""
Unit tests for transport setup in intervals_mcp_server.server_setup.
"""

import os
import pathlib
import sys
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from intervals_mcp_server.server_setup import setup_transport
from intervals_mcp_server.utils.types import TransportAliases


def test_setup_transport_defaults_to_stdio(monkeypatch):
    monkeypatch.delenv("MCP_TRANSPORT", raising=False)
    assert setup_transport() == TransportAliases.STDIO


def test_setup_transport_http_maps_to_streamable_http(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    assert setup_transport() == TransportAliases.STREAMABLE_HTTP


def test_setup_transport_streamable_http(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")
    assert setup_transport() == TransportAliases.STREAMABLE_HTTP


def test_setup_transport_sse_emits_deprecation_warning(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "sse")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = setup_transport()
    assert result == TransportAliases.SSE
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(deprecations) == 1
    assert "deprecated" in str(deprecations[0].message).lower()


def test_setup_transport_invalid_raises(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "invalid")
    try:
        setup_transport()
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Unsupported MCP_TRANSPORT value" in str(exc)
