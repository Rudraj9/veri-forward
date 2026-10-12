"""Opt-in real retrieval/inference smoke checks, not an accuracy evaluation."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieval", action="store_true")
    parser.add_argument("--models", action="store_true")
    parser.add_argument("--url", help="Public publisher URL for real extraction")
    args = parser.parse_args()
    if args.retrieval:
        from core.news_search import search_news
        rows = search_news("RBI repo rate", max_results=3)
        print(f"RSS returned {len(rows)} actual entries.")
        for row in rows:
            print(row)
    if args.url:
        from core.scraper import extract_article
        result = extract_article(args.url)
        print({k: v for k, v in result.items() if k != "text"}, "characters:", len(result["text"]))
    if args.models:
        from core.schemas import Article, Evidence
        from core.similarity import get_model
        from core.evidence_checker import assess
        get_model()
        item = Evidence(article=Article(link="https://example.com"), excerpt="A man is not eating pizza.", relevance=1)
        scored = assess("A man is eating pizza.", [item])[0]
        print({"support": scored.support, "contradiction": scored.contradiction, "neutral": scored.neutral})
    if not (args.retrieval or args.models or args.url):
        parser.error("Select --retrieval, --models or --url")
