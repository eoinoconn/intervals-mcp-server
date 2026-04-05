"""
Tests for OAuth header extraction functionality.
"""
import sys
import pathlib

# Add src to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from intervals_mcp_server.tools.activities import _extract_api_key_from_headers
from intervals_mcp_server.tools.events import _extract_api_key_from_headers as events_extract


def test_extract_api_key_bearer_token():
    """Test extracting API key from Bearer token format."""
    headers = {"authorization": "Bearer my_secret_api_key_123"}
    result = _extract_api_key_from_headers(headers)
    assert result == "my_secret_api_key_123"


def test_extract_api_key_capital_bearer():
    """Test extracting API key from capitalized Authorization header.""" 
    headers = {"Authorization": "Bearer another_api_key_456"}
    result = _extract_api_key_from_headers(headers)
    assert result == "another_api_key_456"


def test_extract_api_key_direct_format():
    """Test extracting API key from direct format (no Bearer prefix)."""
    headers = {"authorization": "direct_api_key_789"}
    result = _extract_api_key_from_headers(headers)
    assert result == "direct_api_key_789"


def test_extract_api_key_no_header():
    """Test handling missing authorization header."""
    headers = {"user-agent": "test"}
    result = _extract_api_key_from_headers(headers)
    assert result == ""


def test_extract_api_key_empty_headers():
    """Test handling empty headers dict."""
    headers = {}
    result = _extract_api_key_from_headers(headers)
    assert result == ""


def test_extract_api_key_empty_auth():
    """Test handling empty authorization header."""
    headers = {"authorization": ""}
    result = _extract_api_key_from_headers(headers)
    assert result == ""


def test_events_extract_api_key():
    """Test that events module extraction works the same way."""
    headers = {"authorization": "Bearer events_api_key_999"}
    result = events_extract(headers)
    assert result == "events_api_key_999"


def test_bearer_with_extra_spaces():
    """Test Bearer token with extra spaces."""
    headers = {"authorization": "Bearer   spaced_key_123   "}
    result = _extract_api_key_from_headers(headers)
    assert result == "  spaced_key_123   "  # Should preserve trailing spaces for now