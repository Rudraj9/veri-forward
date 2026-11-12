"""Escaped HTML views for the verification flow; no verification decisions here."""
from datetime import timezone
from email.utils import parsedate_to_datetime
from html import escape
from urllib.parse import urlsplit


VERDICTS = {
    "supported": ("✓", "Supported", "supported", "The evidence backs this claim."),
    "contradicted": ("×", "Contradicted", "contradicted", "The evidence challenges this claim."),
    "mixed_or_misleading": ("≈", "Mixed or misleading", "mixed", "There’s more to the story."),
    "insufficient_evidence": ("?", "Insufficient evidence", "insufficient", "This claim needs more evidence."),
}


def scanning_html(message="Retrieving related coverage"):
    stage = 0
    if message.startswith("Extracting"):
        stage = 1
    elif message.startswith("Ranking"):
        stage = 2
    steps = "".join(
        f'<div class="scan-step {"done" if i < stage else "current" if i == stage else ""}">'
        f'<span>{"✓" if i < stage else f"0{i + 1}"}</span>{label}</div>'
        for i, label in enumerate(("Find coverage", "Read sources", "Assess evidence"))
    )
    return f'''<section class="scan-panel" role="status" aria-live="polite">
      <div class="scan-top"><span class="eyebrow">INVESTIGATION IN PROGRESS</span><span class="live-pill"><i></i> LIVE</span></div>
      <div class="scan-body">
        <div class="scanner" aria-hidden="true"><div class="scanner-grid"></div><div class="scanner-sweep"></div>
          <div class="scanner-core">⌕</div><i class="scan-point point-one"></i><i class="scan-point point-two"></i><i class="scan-point point-three"></i></div>
        <div class="scan-copy"><h3>Following the evidence<span class="scan-dots">…</span></h3>
          <p>{escape(message)}</p><small>Good checks take a little time. First use may also load models.</small></div>
      </div><div class="scan-steps">{steps}</div>
      <div class="scan-track" aria-hidden="true"><span></span></div>
    </section>'''


def result_html(result):
    icon, label, tone, headline = VERDICTS[result.verdict]
    strength = {"limited": 1, "moderate": 2, "strong": 3}[result.evidence_strength]
    segments = "".join(f'<i class="{"filled" if i < strength else ""}"></i>' for i in range(3))
    supports, contradicts = len(result.supporting_evidence), len(result.contradicting_evidence)
    total = supports + contradicts
    balance = (
        f'<div class="evidence-balance" role="img" aria-label="{supports} supporting passages and {contradicts} contradicting passages">'
        f'<span class="balance-support" style="width:{supports / total * 100:.2f}%"></span>'
        f'<span class="balance-contradict" style="width:{contradicts / total * 100:.2f}%"></span></div>'
        if total else '<div class="evidence-balance empty"></div>'
    )
    status_label = {"completed": "Check complete", "limited": "Check with limitations", "system_error": "Check interrupted"}[result.status]
    return f'''<section class="result-dashboard {tone}">
      <div class="result-top"><span class="eyebrow">YOUR EVIDENCE BRIEF</span><span class="result-status {result.status}">{status_label}</span></div>
      <div class="result-body"><div class="verdict-orb" aria-hidden="true"><div class="verdict-orb-inner">{icon}</div></div>
        <div class="result-copy"><span class="verdict-label">{label}</span><h2>{headline}</h2><p>{escape(result.explanation)}</p></div></div>
      <div class="claim-receipt"><span class="eyebrow">THE CLAIM YOU CHECKED</span><p>“{escape(result.reviewed_claim)}”</p></div>
    </section>
    <div class="result-metrics">
      <div class="insight-card"><span class="insight-icon">◒</span><span class="insight-label">Evidence strength</span><strong>{result.evidence_strength.title()}</strong><div class="strength-segments" aria-hidden="true">{segments}</div><small>Strength of the available evidence</small></div>
      <div class="insight-card"><span class="insight-icon">▤</span><span class="insight-label">Related coverage</span><strong>{len(result.related_articles):02d}<em> articles</em></strong><small>Related coverage alone does not verify a claim</small></div>
      <div class="insight-card"><span class="insight-icon">⇄</span><span class="insight-label">Qualifying passages</span><strong>{total:02d}<em> passages</em></strong>{balance}<small><b class="support-label">{supports} supporting</b> · <b class="contradict-label">{contradicts} contradicting</b></small></div>
    </div>'''


def evidence_heading_html(title, count, tone):
    return f'<div class="evidence-heading {tone}"><span>{"↗" if tone == "support" else "↘"}</span><h3>{escape(title)}</h3><b>{count:02d}</b></div>'


def evidence_card_html(item, index, tone):
    return f'''<article class="passage-card {tone}">
      <div class="passage-top"><span class="source-mark">{escape((item.article.source or "?")[0].upper())}</span><b>{escape(item.article.source)}</b><small>PASSAGE {index:02d}</small></div>
      <blockquote>{escape(item.excerpt)}</blockquote>
      <a href="{escape(item.article.publisher_url or item.article.link, quote=True)}" target="_blank" rel="noopener noreferrer">{escape(item.article.title or "Read publisher source")} <span>↗</span></a>
      <div class="passage-date">Published: {escape(friendly_date(item.article.published) or "not available")}<br>Page metadata: {escape(friendly_date(item.article.publisher_published) or "not available")} · Event date not inferred</div>
    </article>'''


def empty_evidence_html(tone):
    return f'''<div class="empty-evidence {tone}"><span aria-hidden="true">◎</span><b>No qualifying passages</b><p>No passages met the criteria for this side of the claim. Missing evidence does not establish whether a claim is true or false.</p><p>Try rephrasing with the exact names, date and quantity, or review the related coverage below.</p></div>'''


# Plain-language replacements for the pipeline's extraction_status enum.
EXTRACTION_NOTES = {
    "not_attempted": "not fetched",
    "empty": "no article text",
    "failed": "fetch failed",
    "google_news_unresolved": "publisher link unresolved",
}


def source_key(article):
    """Match an article across related_articles and the assessed evidence lists."""
    return (article.publisher_url or article.link or "").rstrip("/").casefold()


def friendly_date(raw):
    """RSS dates are RFC 822; show a short, unambiguous UTC form instead."""
    if not raw:
        return None
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return raw
    if parsed is None:
        return raw
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%d %b %Y, %H:%M UTC")


def related_coverage_html(result):
    """Group sources by the role they actually played in this check."""
    supporting = {source_key(e.article) for e in result.supporting_evidence}
    contradicting = {source_key(e.article) for e in result.contradicting_evidence}

    def role(article):
        key = source_key(article)
        if key in supporting:
            return "support", "Supports claim"
        if key in contradicting:
            return "contradict", "Challenges claim"
        if article.extraction_status != "extracted":
            return "muted", EXTRACTION_NOTES.get(article.extraction_status, "could not read")
        return "muted", "Related only"

    def sort_key(article):
        tone, _ = role(article)
        try:
            stamp = parsedate_to_datetime(article.published).timestamp() if article.published else 0
        except (TypeError, ValueError, IndexError):
            stamp = 0
        return (0 if tone != "muted" else 1, -stamp, article.title.casefold())

    articles = sorted(result.related_articles, key=sort_key)
    if not articles:
        return '<div class="empty-evidence"><span aria-hidden="true">◎</span><b>No related coverage found</b><p>Nothing was retrieved for this claim. That is a retrieval limit, not evidence that the claim is false.</p><p>Paste a clearer claim, or open a direct publisher link, and try again.</p></div>'

    cards = []
    for article in articles:
        tone, label = role(article)
        url = article.publisher_url or article.link
        date = friendly_date(article.published)
        duplicates = list(dict.fromkeys(u for u in article.duplicate_urls if u and u != url))[:3]
        dup_html = ""
        if duplicates:
            # A hostname tells the reader "same story, another outlet"; "link 1" does not.
            links = ", ".join(
                f'<a href="{escape(u, quote=True)}" target="_blank" rel="noopener noreferrer">'
                f'{escape((urlsplit(u).hostname or "").removeprefix("www.") or u)}</a>'
                for u in duplicates
            )
            dup_html = f'<div class="source-dup">Also published at {links}</div>'
        cards.append(f'''<article class="source-card {tone}">
      <div class="source-head"><span class="source-mark" aria-hidden="true">{escape((article.source or "?")[0].upper())}</span><span class="source-name">{escape(article.source or "Unknown source")}</span><span class="source-badge {tone}">{escape(label)}</span></div>
      <a class="source-title" href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{escape(article.title or "Untitled coverage")}<span aria-hidden="true"> ↗</span></a>
      <div class="source-meta">{escape(date) if date else "Publication date unavailable"}</div>{dup_html}
    </article>''')

    used = sum(1 for article in articles if role(article)[0] != "muted")
    return (
        f'<div class="source-summary">{len(articles)} article{"s" if len(articles) != 1 else ""} retrieved · '
        f'{used} used as evidence. Related coverage is context, not proof: only passages that passed the '
        f'retrieval and NLI rules count. Dates are publication dates, not event dates.</div>'
        f'<div class="source-grid">{"".join(cards)}</div>'
    )
