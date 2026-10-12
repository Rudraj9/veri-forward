"""Escaped HTML views for the verification flow; no verification decisions here."""
from html import escape


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
      <div class="passage-date">RSS publication: {escape(item.article.published or "not available")}<br>Publisher metadata: {escape(item.article.publisher_published or "not available")} · Event date not inferred</div>
    </article>'''


def empty_evidence_html(tone):
    return f'''<div class="empty-evidence {tone}"><span aria-hidden="true">◎</span><b>No qualifying passages</b><p>No passages met the criteria for this side of the claim. Missing evidence does not establish whether a claim is true or false.</p></div>'''
