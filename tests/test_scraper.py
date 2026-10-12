from unittest.mock import patch
from core.scraper import extract_article, publisher_link


def test_google_wrapper_is_not_article_text():
    with patch("core.scraper.fetch", return_value=(b"<html>Google News wrapper</html>", "https://news.google.com/rss/articles/token", "text/html")):
        result = extract_article("https://news.google.com/rss/articles/token")
    assert result["text"] == ""
    assert result["extraction_status"] == "google_news_unresolved"


def test_only_unambiguous_publisher_link():
    html = b'<a href="https://publisher.example/story">Read</a>'
    assert publisher_link(html, "https://news.google.com/a", "https://publisher.example") == "https://publisher.example/story"
    assert publisher_link(html + b'<a href="https://publisher.example/other">Other</a>', "https://news.google.com/a", "https://publisher.example") is None


def test_actual_publisher_html_extraction():
    from pathlib import Path
    html = (Path(__file__).parent / "fixtures/article.html").read_bytes()
    with patch("core.scraper.fetch", return_value=(html, "https://publisher.example/story", "text/html")):
        result = extract_article("https://publisher.example/story")
    assert "did not raise" in result["text"]
    assert result["publisher_published"] == "2025-01-01T10:00:00Z"
