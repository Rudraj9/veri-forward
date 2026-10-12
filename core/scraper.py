"""Trafilatura extraction; Google News intermediary pages are never evidence."""
from urllib.parse import urlsplit, urljoin
from html.parser import HTMLParser
from core.http_client import fetch


class PageLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.publication = None

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag == "meta" and (attrs.get("property") or attrs.get("name")) == "article:published_time":
            self.publication = attrs.get("content")


def publisher_link(body, wrapper_url, publisher_hint):
    """Only follow an unambiguous visible publisher article link, never guess one."""
    host = (urlsplit(publisher_hint or "").hostname or "").removeprefix("www.")
    if not host:
        return None
    parser = PageLinks()
    parser.feed(body.decode("utf-8", errors="replace"))
    links = []
    for href in parser.links:
        candidate = urljoin(wrapper_url, href)
        parts = urlsplit(candidate)
        if parts.scheme in ("http", "https") and (parts.hostname or "").removeprefix("www.") == host and parts.path not in ("", "/"):
            links.append(candidate)
    links = list(dict.fromkeys(links))
    return links[0] if len(links) == 1 else None


def extract_article(url, publisher_hint=None):
    body, final_url, content_type = fetch(url)
    host = (urlsplit(final_url).hostname or "").lower()
    if host == "news.google.com" or host.endswith(".news.google.com"):
        direct = publisher_link(body, final_url, publisher_hint)
        if not direct:
            return {"publisher_url": None, "text": "", "extraction_status": "google_news_unresolved"}
        body, final_url, content_type = fetch(direct)
        host = (urlsplit(final_url).hostname or "").lower()
        if host == "news.google.com" or host.endswith(".news.google.com"):
            return {"publisher_url": None, "text": "", "extraction_status": "google_news_unresolved"}
    if "html" not in content_type and "text/plain" not in content_type:
        raise ValueError("Article response is not HTML or plain text")
    import trafilatura
    text = trafilatura.extract(body, include_comments=False, include_tables=False) or ""
    metadata = PageLinks()
    metadata.feed(body.decode("utf-8", errors="replace"))
    return {"publisher_url": final_url, "publisher_published": metadata.publication,
            "text": text[:50000], "extraction_status": "extracted" if text else "empty"}
