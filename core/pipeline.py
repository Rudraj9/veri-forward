"""Shared retrieval -> extraction -> relevance -> NLI -> verdict orchestration."""
import re
from difflib import SequenceMatcher
from urllib.parse import urlsplit, urlunsplit
from core.schemas import Article, VerifyRequest, VerifyResponse
from core.claim_extractor import query_variants
from core.news_search import search_news
from core.scraper import extract_article
from core.similarity import rank_passages
from core.evidence_checker import assess
from core.verdict import decide, explain
from utils.config import settings


def normalized_url(url):
    p = urlsplit(url)
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), p.query, ""))


def publisher_group(url):
    """Use a bundled public suffix list, without downloading it at runtime."""
    import tldextract
    parts = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)(url)
    return parts.top_domain_under_public_suffix or parts.domain


def deduplicate(articles):
    unique = []
    for article in articles:
        title = re.sub(r"\W+", " ", article.title.casefold()).strip()
        match = next((a for a in unique if normalized_url(a.publisher_url or a.link) == normalized_url(article.publisher_url or article.link)
                      or (title and title == re.sub(r"\W+", " ", a.title.casefold()).strip())
                      or (a.text and article.text and SequenceMatcher(None, a.text[:10000], article.text[:10000], autojunk=False).ratio() > 0.85)), None)
        if match:
            match.provenance = list(dict.fromkeys(match.provenance + article.provenance))
            match.duplicate_urls = list(dict.fromkeys(match.duplicate_urls + [article.link] + article.duplicate_urls))
            if not match.text and article.text:
                match.text, match.publisher_url, match.extraction_status = article.text, article.publisher_url, article.extraction_status
                match.publisher_published = article.publisher_published
        else:
            unique.append(article)
    for article in unique:
        # Registered domain is a proxy for independence, not proof of it.
        article.independence_group = publisher_group(article.publisher_url or article.link)
    return unique


def verify(request: VerifyRequest, progress=None):
    report = progress or (lambda message: None)
    warnings = ["Automated entity/date/location/quantity checks are incomplete.",
                "Publisher domains only approximate independence; undetected syndication or shared ownership may remain.",
                "Publication dates are not event dates. Similarity and NLI scores are not truth probabilities."]
    failures, articles, evidence = [], [], []
    claim = request.reviewed_claim.strip()
    report("Retrieving related coverage")
    if request.input_type == "url":
        # API clients must prepare/review the claim first, but supplied URL is evidence too.
        from core.http_client import validate_url
        validate_url(request.content)
        articles.append(Article(title="User supplied article", link=request.content, provenance=["user_url"]))
    batches = []
    for query in query_variants(claim, settings.official_domains):
        try:
            batches.append([Article(**a, provenance=[query]) for a in search_news(query, max_results=settings.max_articles)])
        except Exception as exc:
            failures.append(f"Search failed ({type(exc).__name__}): {exc}")
    # Interleave query batches so a full first query cannot crowd out variants.
    for index in range(settings.max_articles):
        articles.extend(batch[index] for batch in batches if index < len(batch))
    articles = deduplicate(articles)[:settings.max_articles]
    report("Extracting publisher articles")
    for index, article in enumerate(articles, start=1):
        report(f"Extracting article {index}/{len(articles)}")
        try:
            for key, value in extract_article(article.link, publisher_hint=article.source_url).items():
                setattr(article, key, value)
            if article.extraction_status != "extracted":
                failures.append(f"{article.link}: {article.extraction_status}; title is related coverage only")
        except Exception as exc:
            article.extraction_status = "failed"
            failures.append(f"Extraction failed for {article.link} ({type(exc).__name__}): {exc}")
    articles = deduplicate(articles)
    if any(a.text for a in articles):
        report("Ranking passages and checking evidence")
        try:
            evidence = rank_passages(claim, articles)
            evidence = assess(claim, evidence)
        except Exception as exc:
            failures.append(f"Model assessment unavailable ({type(exc).__name__}): {exc}")
            # Never permit partly assessed results to issue a verdict after failure.
            for item in evidence:
                item.eligible = False
    verdict, strength, supports, contradicts = decide(evidence)
    explanation = explain(verdict)
    status = "limited" if failures else "completed"
    if any(f.startswith("Model assessment unavailable") for f in failures) or (not articles and failures) or (articles and all(a.extraction_status == "failed" for a in articles)):
        status = "system_error"
    if failures:
        explanation += " Retrieval, extraction or model limitations affected this check; see the recorded failures."
    links = list(dict.fromkeys(e.article.publisher_url for e in supports + contradicts if e.article.publisher_url))[:4]
    reply = f'Claim: {claim}\nVeriForward: {verdict.replace("_", " ")}. {explanation}\nPublisher independence and automated context checks are uncertain.'
    if links:
        reply += "\nEvidence sources:\n" + "\n".join(links)
    elif articles:
        reply += "\nRelated coverage only (does not verify the claim):\n" + "\n".join(a.publisher_url or a.link for a in articles[:3])
    return VerifyResponse(status=status, original_input=request.content, reviewed_claim=claim, verdict=verdict,
        explanation=explanation, evidence_strength=strength, supporting_evidence=supports,
        contradicting_evidence=contradicts, assessed_evidence=evidence, related_articles=articles,
        warnings=warnings, failures=failures, whatsapp_reply=reply)
