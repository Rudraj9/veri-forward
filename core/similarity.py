# Semantic embedding generation and cosine similarity matching using sentence-transformers
"""
core/similarity.py
Compares a claim against a list of news article titles using sentence embeddings,
to rank related coverage. Relevance cannot establish factual correctness.
"""

import sys
from pathlib import Path
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from functools import lru_cache
import threading
from utils.config import settings

# Load the model once at module level — reused across all calls, not reloaded each time.
_load_lock = threading.Lock()


@lru_cache(maxsize=1)
def _load_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.embedding_model, device="cpu")


def get_model():
    with _load_lock:
        return _load_model()


def rank_articles_by_similarity(claim: str, articles: list[dict]) -> list[dict]:
    """
    Compare a claim against a list of articles (title-only) and rank them by similarity.

    Args:
        claim: The claim/topic text to verify.
        articles: List of dicts from news_search.search_news(), each with a "title" key.

    Returns:
        The same list of article dicts, each with an added "similarity" score (0 to 1),
        sorted from most to least similar.
    """
    if not claim or not claim.strip() or not articles:
        return []

    # Encode the claim once
    from sentence_transformers import util
    model = get_model()
    claim_embedding = model.encode(claim, convert_to_tensor=True)

    # Encode all article titles in one batch (faster than one-by-one)
    titles = [article["title"] for article in articles]
    title_embeddings = model.encode(titles, convert_to_tensor=True)

    # Compute cosine similarity between claim and every title
    scores = util.cos_sim(claim_embedding, title_embeddings)[0]

    # Attach scores back to their articles
    articles = [dict(article) for article in articles]
    for article, score in zip(articles, scores):
        article["similarity"] = round(float(score), 4)

    # Sort by similarity, highest first
    ranked = sorted(articles, key=lambda a: a["similarity"], reverse=True)
    return ranked


def get_best_match(claim: str, articles: list[dict]) -> dict | None:
    """
    Convenience function — returns just the single best-matching article, or None
    if no articles were provided.
    """
    ranked = rank_articles_by_similarity(claim, articles)
    return ranked[0] if ranked else None


def rank_passages(claim, articles):
    from sentence_transformers import util
    from core.schemas import Evidence
    model = get_model()
    candidates = []
    for article in articles:
        ids = model.tokenizer.encode(article.text, add_special_tokens=False)
        width = min(model.max_seq_length - 2, 220)
        for start in range(0, min(len(ids), 4000), width - 40):
            excerpt = model.tokenizer.decode(ids[start:start + width], skip_special_tokens=True)
            if excerpt.strip():
                candidates.append((article, excerpt))
    if not candidates:
        return []
    scores = util.cos_sim(model.encode(claim), model.encode([p[1] for p in candidates]))[0]
    evidence = [Evidence(article=a, excerpt=p, relevance=float(s)) for (a, p), s in zip(candidates, scores)]
    return sorted(evidence, key=lambda e: e.relevance, reverse=True)[:settings.max_passages]


if __name__ == "__main__":
    # Quick manual test — run this file directly:
    #   python core/similarity.py
    from core.news_search import search_news

    test_claim = "RBI repo rate hike"

    print(f"Claim: {test_claim}\n")
    print("Fetching related articles...\n")
    articles = search_news(test_claim, max_results=5)

    if not articles:
        print("No articles found to compare against.")
    else:
        ranked = rank_articles_by_similarity(test_claim, articles)
        for i, article in enumerate(ranked, start=1):
            print(f"{i}. [{article['similarity']:.3f}] {article['title']}")
            print(f"   Source: {article['source']}")
            print(f"   Link: {article['link']}\n")

        best = ranked[0]
        print(f"Best match: \"{best['title']}\" (similarity: {best['similarity']:.3f})")
