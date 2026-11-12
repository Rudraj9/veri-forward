"""Display-layer checks: source cards group by role, humanise dates, escape text."""
from core.schemas import Article, Evidence, VerifyResponse
from app.visuals import friendly_date, related_coverage_html


def article(**overrides):
    base = dict(
        title="Report", link="https://one.example/a", source="One",
        publisher_url="https://one.example/a", extraction_status="extracted", text="body",
    )
    base.update(overrides)
    return Article(**base)


def result(supporting=(), contradicting=(), articles=()):
    return VerifyResponse(
        original_input="claim", reviewed_claim="claim", verdict="insufficient_evidence",
        explanation="e", evidence_strength="limited", supporting_evidence=list(supporting),
        contradicting_evidence=list(contradicting), related_articles=list(articles),
        whatsapp_reply="reply",
    )


def evidence(item, support=0.97, contradiction=0.01):
    return Evidence(article=item, excerpt="passage", relevance=0.9, support=support,
                    contradiction=contradiction, neutral=0.02, eligible=True)


def test_cards_are_grouped_by_the_role_they_played():
    yes, no = article(), article(title="Other", link="https://two.example/b", source="Two", publisher_url="https://two.example/b")
    html = related_coverage_html(result(supporting=[evidence(yes)], articles=[yes, no]))
    assert "Supports claim" in html
    assert "Related only" in html
    assert "2 articles retrieved" in html
    assert "1 used as evidence" in html


def test_extraction_failures_use_plain_language():
    broken = article(extraction_status="google_news_unresolved", publisher_url=None)
    html = related_coverage_html(result(articles=[broken]))
    assert "publisher link unresolved" in html
    assert "google_news_unresolved" not in html


def test_untrusted_article_text_is_escaped():
    hostile = article(title="<script>alert(1)</script>", source="<b>Bad</b>")
    html = related_coverage_html(result(articles=[hostile]))
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_rss_dates_are_humanised():
    formatted = friendly_date("Mon, 11 Nov 2025 10:00:00 GMT")
    assert "2025" in formatted and formatted.endswith("10:00 UTC")
    assert friendly_date("") is None
    assert friendly_date("not a date") == "not a date"


def test_duplicate_urls_are_named_by_host():
    syndicated = article(duplicate_urls=["https://www.mirror.example/copy", "https://other.example/copy"])
    html = related_coverage_html(result(articles=[syndicated]))
    assert "mirror.example" in html and "other.example" in html
    assert "link 1" not in html


def test_empty_coverage_states_it_is_a_retrieval_limit():
    html = related_coverage_html(result(articles=[]))
    assert "No related coverage found" in html
    assert "not evidence that the claim is false" in html
