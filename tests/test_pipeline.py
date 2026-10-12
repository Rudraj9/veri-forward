"""Offline fixtures and mock scores test orchestration, not model accuracy."""
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from core.schemas import Article, Evidence, VerifyRequest, VerifyResponse
from core.pipeline import verify, deduplicate
from core.evidence_checker import context_checks
from core.verdict import decide

FIXTURE = json.loads((Path(__file__).parent / "fixtures/evidence.json").read_text())


def evidence(host="one.example", support=0.02, contradiction=0.96, excerpt=None):
    article = Article(link=f"https://{host}/report", publisher_url=f"https://{host}/report", title="Rate report", independence_group=host, text=excerpt or FIXTURE["denial"])
    return Evidence(article=article, excerpt=article.text, relevance=0.95, support=support, contradiction=contradiction, neutral=0.02, eligible=True)


def request():
    return VerifyRequest(content=FIXTURE["claim"], reviewed_claim=FIXTURE["claim"])


def test_similarly_worded_denial_does_not_support():
    result = decide([evidence(), evidence("two.example")])
    assert result[0] == "contradicted"
    assert not result[2]


def test_no_results():
    with patch("core.pipeline.search_news", return_value=[]):
        result = verify(request())
    assert result.verdict == "insufficient_evidence"
    assert not result.related_articles


def test_search_failure():
    with patch("core.pipeline.search_news", side_effect=OSError("offline")):
        result = verify(request())
    assert result.verdict == "insufficient_evidence"
    assert len(result.failures) == 2
    assert result.status == "system_error"


def test_extraction_failure():
    with patch("core.pipeline.search_news", return_value=[{"title": "Report", "link": "https://one.example/a"}]), patch("core.pipeline.extract_article", side_effect=OSError("blocked")):
        result = verify(request())
    assert result.verdict == "insufficient_evidence"
    assert result.related_articles[0].extraction_status == "failed"


def test_model_unavailable_abstains_even_after_partial_assessment():
    item = evidence()
    with patch("core.pipeline.search_news", return_value=[{"title": "Report", "link": item.article.link}]), patch("core.pipeline.extract_article", return_value={"text": item.excerpt, "publisher_url": item.article.link, "extraction_status": "extracted"}), patch("core.pipeline.rank_passages", return_value=[item]), patch("core.pipeline.assess", side_effect=OSError("model unavailable")):
        result = verify(request())
    assert result.verdict == "insufficient_evidence"
    assert not item.eligible
    assert result.status == "system_error"
    assert any("Model assessment unavailable" in f for f in result.failures)


def test_duplicate_and_syndicated_articles():
    a = evidence().article
    b = evidence("two.example").article
    a.provenance, b.provenance = ["q1"], ["q2"]
    merged = deduplicate([a, b])
    assert len(merged) == 1
    assert merged[0].provenance == ["q1", "q2"]
    assert b.link in merged[0].duplicate_urls


def test_one_article_many_passages_is_not_corroboration():
    assert decide([evidence(), evidence()])[0] == "insufficient_evidence"


def test_conflicting_evidence():
    assert decide([evidence(), evidence("two.example", support=0.96, contradiction=0.02)])[0] == "mixed_or_misleading"


@pytest.mark.parametrize("key", ["changed_date", "changed_location", "changed_quantity"])
def test_context_mismatch(key):
    assert context_checks(FIXTURE["claim"], FIXTURE[key])


def test_negation_preserved():
    from core.claim_extractor import extract_claims, query_variants
    assert extract_claims(FIXTURE["denial"])[0].startswith("RBI did not")
    assert all(q.startswith(FIXTURE["denial"]) for q in query_variants(FIXTURE["denial"]))


def test_shared_schema_roundtrip():
    with patch("core.pipeline.search_news", return_value=[]):
        result = verify(request())
    assert VerifyResponse.model_validate_json(result.model_dump_json()) == result
