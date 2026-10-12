import socket
from unittest.mock import patch, MagicMock
import pytest
from core.http_client import validate_url, fetch, _cache
from urllib.parse import urlsplit


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com", "http://user:pass@example.com", "https://example.com:9000", "nonsense"])
def test_invalid_url(url):
    with pytest.raises(ValueError):
        validate_url(url)


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.1", "192.168.1.1", "169.254.169.254", "::1", "fc00::1", "0.0.0.0", "224.0.0.1"])
def test_private_dns(ip):
    with patch("core.http_client.socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 80))]):
        with pytest.raises(ValueError):
            validate_url("http://example.com")


def test_redirect_to_private_is_blocked():
    _cache.clear()
    response = MagicMock(status=302)
    response.getheader.return_value = "http://127.0.0.1/secret"
    connection = MagicMock()
    connection.getresponse.return_value = response
    def dns(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1" if host == "127.0.0.1" else "8.8.8.8", 80))]
    with patch("core.http_client.socket.getaddrinfo", side_effect=dns), patch("core.http_client.socket.create_connection"), patch("core.http_client.http.client.HTTPConnection", return_value=connection):
        with pytest.raises(ValueError, match="Non-public"):
            fetch("http://example.com")


def test_success_cache_and_response_limit():
    _cache.clear()
    response = MagicMock(status=200)
    response.getheader.return_value = "text/html"
    response.read1.side_effect = [b"saved fixture body", b""]
    connection = MagicMock()
    connection.getresponse.return_value = response
    with patch("core.http_client.validate_url", side_effect=lambda u: (urlsplit(u), "8.8.8.8")), patch("core.http_client.socket.create_connection"), patch("core.http_client.http.client.HTTPConnection", return_value=connection), patch("core.http_client.time.sleep"):
        assert fetch("http://example.com/fixture")[0] == b"saved fixture body"
        assert fetch("http://example.com/fixture")[0] == b"saved fixture body"
        assert connection.request.call_count == 1
        response.read1.side_effect = [b"x" * 2_000_001]
        with pytest.raises(ValueError, match="2 MB"):
            fetch("http://example.com/oversized")
