# Real-time live news article retrieval via Google News RSS
"""
core/news_search.py
Fetches live, related news articles from Google News RSS for a given claim/topic.
No API key required — Google News RSS is a public feed.
"""

import time
import urllib.parse
import sys
from pathlib import Path
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import feedparser
from core.http_client import fetch


def search_news(query: str, max_results: int = 5, region: str = "IN", lang: str = "en") -> list[dict]:
    """
    Search Google News RSS for articles related to the given query.

    Args:
        query: The claim or topic to search for.
        max_results: Maximum number of articles to return.
        region: Country code for results (e.g. "IN", "US").
        lang: Language code for results (e.g. "en", "hi").

    Returns:
        A list of dicts, each with: title, link, published, source.
    """
    if not query or not query.strip():
        return []

    encoded_query = urllib.parse.quote(query.strip())
    ceid = f"{region}:{lang}"
    url = (
        f"https://news.google.com/rss/search?q={encoded_query}"
        f"&hl={lang}-{region}&gl={region}&ceid={ceid}"
    )

    body, _, _ = fetch(url)
    feed = feedparser.parse(body)
    if feed.bozo and not feed.entries:
        raise ValueError("RSS could not be parsed")

    results = []
    for entry in feed.entries[:max_results]:
        results.append({
            "title": entry.get("title", "").strip(),
            "link": entry.get("link", "").strip(),
            "published": entry.get("published", ""),
            "source_url": entry.get("source", {}).get("href") if isinstance(entry.get("source"), dict) else None,
            "source": entry.get("source", {}).get("title", "Unknown source")
                       if isinstance(entry.get("source"), dict) else "Unknown source",
        })

    return results


if __name__ == "__main__":
    # Quick manual test — run this file directly:
    #   python core/news_search.py
    test_query = "RBI repo rate hike"

    print(f"Searching for: {test_query}\n")
    articles = search_news(test_query, max_results=5)

    if not articles:
        print("No articles found. Try a different query or check your internet connection.")
    else:
        for i, article in enumerate(articles, start=1):
            print(f"{i}. {article['title']}")
            print(f"   Source: {article['source']}")
            print(f"   Published: {article['published']}")
            print(f"   Link: {article['link']}\n")
            time.sleep(0.2)  # small delay, polite to the feed
