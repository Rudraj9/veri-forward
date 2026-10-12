"""Bounded public HTTP fetching with DNS-pinned sockets and validated redirects."""
import http.client
import ipaddress
import socket
import ssl
import threading
import time
from collections import OrderedDict
from urllib.parse import urlsplit, urljoin

_cache = OrderedDict()
_lock = threading.Lock()
_last = 0.0


def validate_url(url):
    try:
        p = urlsplit(url)
        if p.scheme not in ("http", "https") or not p.hostname:
            raise ValueError("Only HTTP/HTTPS URLs are allowed")
        if p.username or p.password or p.port not in (None, 80, 443):
            raise ValueError("Credentials and nonstandard ports are blocked")
        ips = list(dict.fromkeys(a[4][0] for a in socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)))
        if not ips or any(not ipaddress.ip_address(ip).is_global or ipaddress.ip_address(ip).is_multicast or ipaddress.ip_address(ip).is_reserved for ip in ips):
            raise ValueError("Non-public destination blocked")
        return p, ips[0]
    except (OSError, ValueError) as exc:
        raise ValueError(f"Invalid or blocked URL: {exc}") from exc


def fetch(url):
    global _last
    with _lock:
        cached = _cache.get(url)
        if cached and time.monotonic() - cached[0] < 300:
            return cached[1]
    original = url
    for redirect in range(4):
        p, ip = validate_url(url)
        result = None
        for attempt in range(2):
            with _lock:
                time.sleep(max(0, 0.5 - (time.monotonic() - _last)))
                _last = time.monotonic()
            conn = http.client.HTTPConnection(p.hostname, p.port or (443 if p.scheme == "https" else 80), timeout=10)
            response = None
            try:
                conn.sock = socket.create_connection((ip, conn.port), timeout=10)
                if p.scheme == "https":
                    conn.sock = ssl.create_default_context().wrap_socket(conn.sock, server_hostname=p.hostname)
                transport = conn.sock
                conn.request("GET", (p.path or "/") + (("?" + p.query) if p.query else ""), headers={"Host": p.netloc, "User-Agent": "VeriForward/0.1", "Accept-Encoding": "identity"})
                response = conn.getresponse()
                if response.status in (301, 302, 303, 307, 308):
                    location = response.getheader("Location")
                    if not location:
                        raise ValueError("Redirect without destination")
                    url = urljoin(url, location)
                    break
                if response.status != 200:
                    raise OSError(f"HTTP {response.status}")
                body = bytearray()
                deadline = time.monotonic() + 30
                while len(body) <= 2_000_000:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise OSError("Response time budget exceeded")
                    transport.settimeout(min(10, remaining))
                    chunk = response.read1(min(65536, 2_000_001 - len(body)))
                    if not chunk:
                        break
                    body.extend(chunk)
                if len(body) > 2_000_000:
                    raise ValueError("Response exceeds 2 MB")
                body = bytes(body)
                result = body, url, response.getheader("Content-Type", "")
                break
            except (OSError, http.client.HTTPException):
                if attempt == 1:
                    raise
            finally:
                if response is not None:
                    response.close()
                conn.close()
        if result is not None:
            with _lock:
                _cache[original] = (time.monotonic(), result)
                while len(_cache) > 64:
                    _cache.popitem(last=False)
            return result
    raise ValueError("Redirect limit exceeded")
